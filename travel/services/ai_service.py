"""
Everything that talks to the Groq AI API lives here.

Why one file? So the API key is used in exactly ONE place. The rest of the
project just calls these functions. The key itself comes from the .env file
through Django settings, and is never sent to the browser.

Groq gives us four things, each with a model that suits the job:

  * chat and translation -> openai/gpt-oss-120b      (handles Telugu well)
  * image recognition    -> qwen/qwen3.6-27b         (the vision model)
  * speech to text       -> whisper-large-v3         (audio to text)

Every model name comes from settings, never from a literal here, because Groq
retires models: this app was pointed at llama-3.3-70b-versatile until Groq
withdrew it, and chat and translation returned 503 until the name was changed.
If they start failing again, list what the key can actually reach with

    curl -H "Authorization: Bearer $GROQ_API_KEY" \
         https://api.groq.com/openai/v1/models

and set GROQ_CHAT_MODEL to one of those. Note that the gpt-oss models reason
before answering and those tokens count against max_tokens, so a budget that
is too small comes back with empty content rather than a short answer.
"""
import base64
import logging
import re

from django.conf import settings

logger = logging.getLogger(__name__)

# The system prompt tells the AI who it is and how to behave.
TRAVEL_SYSTEM_PROMPT = """You are the AI travel assistant inside a web app
called "AI Travel Planner & Smart Trip Assistant". You help customers in India
plan trips.

What you do:
- Suggest destinations and tourist places.
- Build day-by-day itineraries from the number of days, budget, transport and
  number of travellers.
- Explain what the estimated costs are made of.
- Suggest what to pack and how to prepare for a trip.
- Translate between Telugu and English when asked.
- Answer follow-up questions about a trip.

How you must behave:
- If the customer has not told you the starting city, destination, number of
  days or number of travellers, ask for the missing pieces before giving a
  detailed plan. Ask at most two short questions at a time.
- Any price, distance or travel time you mention is an ESTIMATE. Say so.
  Never present a number as a live fare, a live hotel rate, or current
  availability. You cannot check live prices, seats or bookings.
- If you are unsure about a fact, say you are unsure.
- Use Indian rupees and write them like Rs 8,500.
- Keep answers focused and easy to read. Use short paragraphs or small lists.
  A simple question gets a short answer, not a long report.
- Reply in the same language the customer used. If they write in Telugu,
  reply in Telugu.
"""

IMAGE_SYSTEM_PROMPT = """You look at photographs of places and landmarks for a
travel planning app.

Reply with exactly these lines and nothing else:

EVIDENCE: what is visible - tower shape, material, signboard script, landscape
PLACE: the monument's name, or "Not sure"
LOCATION: city, state, country, or "Not sure"
CONFIDENCE: HIGH or LOW
ALTERNATIVES: other monuments that would fit, or "None"
ABOUT: two or three sentences
VISIT: how to get there and when to go (rough estimates only)
NEARBY: two or three places close by

Answer HIGH only if you can name the exact monument and its city; otherwise
LOW. Naming the wrong monument confidently is the worst outcome here, and
"Not sure" with good ALTERNATIVES is a genuinely useful answer.

If the picture is mostly a person, food or a document, say so in PLACE and
answer LOW. Never invent ticket prices, timings or booking details.
"""

# A friendly message shown when the API key is missing, so the whole site
# still works for someone who has not set up a key yet.
NO_KEY_MESSAGE = (
    "The AI assistant is not connected yet. Add your GROQ_API_KEY to the "
    ".env file and restart the server to turn on chat, translation and image "
    "recognition. Everything else on this site (planner, cost calculator, "
    "itinerary) works without it."
)


class AIError(Exception):
    """Raised when we cannot get an answer from the AI service."""


def is_configured():
    """True when an API key is present."""
    return bool(settings.GROQ_API_KEY)


# How long we wait for Groq before giving up. Without this the library waits
# ten minutes, so a stalled request leaves the customer watching a spinner.
REQUEST_TIMEOUT_SECONDS = 30.0

# How hard the chat model thinks before it starts answering. Groq accepts
# "low", "medium" or "high" here - not "none", which is a vision-model
# setting. Travel questions do not need deliberation, and every reasoning
# token is time the customer waits.
CHAT_REASONING_EFFORT = "low"

# One client, kept for the life of the process.
_client = None
_client_key = None


def _get_client():
    """
    Return the Groq client, building it once and reusing it afterwards.

    This used to build a fresh client for every single request, which cost
    between a third and two thirds of a second each time - a new TLS handshake
    to Groq before a word of the question had been sent. Keeping the client
    keeps the connection alive, so that price is paid once at start-up.

    The import is inside the function so the site still runs even if the
    library is missing.
    """
    global _client, _client_key

    try:
        from groq import Groq
    except ImportError as exc:  # pragma: no cover
        raise AIError("The 'groq' package is not installed. Run: pip install groq") from exc

    if not is_configured():
        raise AIError(NO_KEY_MESSAGE)

    # Rebuild if the key changed under us (tests, or a settings reload).
    if _client is None or _client_key != settings.GROQ_API_KEY:
        _client = Groq(
            api_key=settings.GROQ_API_KEY,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=2,
        )
        _client_key = settings.GROQ_API_KEY
    return _client


def _strip_reasoning(text):
    """
    Some models "think out loud" inside <think>...</think> tags before giving
    the real answer. The customer should only see the answer, so we remove
    those parts.

    Returns "" when the reply was nothing but reasoning. That happens when the
    model deliberates until it runs out of room and never reaches its answer,
    and it used to fall back to returning the raw text - which put the model's
    unfiltered second-guessing ("Wait, is that the French flag? No...") on the
    page as though it were the result. An empty string lets the caller say
    plainly that nothing came back, which is the truth and is far less
    alarming than a wall of visible doubt.
    """
    if not text:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # The model ran out of room and never closed the tag: drop the opener and
    # everything after it.
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL).strip()
    return cleaned


def _call(messages, model=None, max_tokens=2000, reasoning_effort=None):
    """One place that actually sends the request and handles every error."""
    import groq

    client = _get_client()
    extra = {}
    if reasoning_effort:
        extra["reasoning_effort"] = reasoning_effort

    try:
        response = client.chat.completions.create(
            model=model or settings.GROQ_CHAT_MODEL,
            max_tokens=max_tokens,
            messages=messages,
            **extra,
        )
    except groq.AuthenticationError as exc:
        logger.warning("Groq auth failed: %s", exc)
        raise AIError("The Groq API key is missing or invalid.") from exc
    except groq.RateLimitError as exc:
        logger.warning("Groq rate limited: %s", exc)
        raise AIError("Too many requests right now. Please try again in a moment.") from exc
    except groq.APITimeoutError as exc:
        logger.warning("Groq timed out after %ss: %s", REQUEST_TIMEOUT_SECONDS, exc)
        raise AIError(
            "The AI service took too long to answer. Please try again, or ask a shorter question."
        ) from exc
    except groq.APIConnectionError as exc:
        logger.warning("Groq connection error: %s", exc)
        raise AIError("Could not reach the AI service. Check your internet connection.") from exc
    except groq.APIStatusError as exc:
        logger.warning("Groq API error %s: %s", exc.status_code, exc)
        # A retired model is worth its own message. Groq withdraws models as
        # newer ones land - llama-3.3-70b-versatile disappeared from under this
        # app - and the generic wording sent us to the logs to find out why,
        # while "please try again" invited a retry that could never work.
        if exc.status_code == 404:
            raise AIError(
                "The configured AI model (%s) is not available on this API key. "
                "It has probably been retired - set GROQ_CHAT_MODEL to a current "
                "model." % (model or settings.GROQ_CHAT_MODEL)
            ) from exc
        raise AIError("The AI service returned an error. Please try again.") from exc

    if not response.choices:
        raise AIError("The AI service sent an empty reply. Please try again.")

    choice = response.choices[0]
    text = _strip_reasoning(choice.message.content)
    if not text:
        # Almost always the model deliberating past its token budget rather
        # than a genuinely blank reply, so say which it was.
        if getattr(choice, "finish_reason", None) == "length":
            raise AIError(
                "The AI ran out of room before it finished answering. "
                "Try again, or ask a shorter question."
            )
        raise AIError("The AI service sent an empty reply. Please try again.")
    return text


# ---------------------------------------------------------------------------
# 1. Chat
# ---------------------------------------------------------------------------
def _chat_messages(user_message, history=None, trip_context=""):
    """Build the message list for a chat turn. Shared by chat and chat_stream."""
    system = TRAVEL_SYSTEM_PROMPT
    if trip_context:
        system += f"\n\nThe customer is currently looking at this trip:\n{trip_context}"

    messages = [{"role": "system", "content": system}]
    for item in (history or [])[-10:]:  # keep the last 10 turns only
        if item.get("content"):
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages


def chat(user_message, history=None, trip_context=""):
    """
    Send one customer message (plus recent history) to the AI.

    history = list of {"role": "user"/"assistant", "content": "..."}
    trip_context = optional text describing the trip the customer is viewing.
    """
    # The chat model reasons before it answers, and those tokens cost time the
    # customer spends watching a spinner - and room the answer itself needs.
    # "low" answers a trip question in about a second instead of up to four,
    # and leaves the budget for the itinerary rather than the deliberation.
    return _call(
        _chat_messages(user_message, history=history, trip_context=trip_context),
        reasoning_effort=CHAT_REASONING_EFFORT,
    )


class _ReasoningFilter:
    """
    Removes <think>...</think> from a reply that arrives piece by piece.

    _strip_reasoning() can only work on a finished answer. While streaming we
    have to decide what to show before the closing tag exists, so this holds
    back anything inside a think block, and holds back the tail of a chunk
    when it might be the start of a tag split across two chunks.
    """

    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self):
        self.buffer = ""
        self.thinking = False

    def feed(self, chunk):
        """Return the part of chunk that is safe to show now."""
        self.buffer += chunk
        out = []
        while self.buffer:
            if self.thinking:
                end = self.buffer.find(self.CLOSE)
                if end == -1:
                    # Keep only what might be a partial closing tag.
                    self.buffer = self.buffer[-len(self.CLOSE) :]
                    break
                self.buffer = self.buffer[end + len(self.CLOSE) :]
                self.thinking = False
                continue

            start = self.buffer.find(self.OPEN)
            if start != -1:
                out.append(self.buffer[:start])
                self.buffer = self.buffer[start + len(self.OPEN) :]
                self.thinking = True
                continue

            # No tag in sight. Show everything except a tail that could still
            # turn into "<think>" once the next chunk arrives.
            keep = 0
            for size in range(min(len(self.OPEN) - 1, len(self.buffer)), 0, -1):
                if self.buffer.endswith(self.OPEN[:size]):
                    keep = size
                    break
            if keep:
                out.append(self.buffer[:-keep])
                self.buffer = self.buffer[-keep:]
            else:
                out.append(self.buffer)
                self.buffer = ""
            break
        return "".join(out)

    def finish(self):
        """Whatever is left once the stream ends."""
        if self.thinking:
            return ""
        left, self.buffer = self.buffer, ""
        return left


def chat_stream(user_message, history=None, trip_context=""):
    """
    The same answer as chat(), but handed over a few words at a time.

    A trip itinerary takes the model a couple of seconds to write. Waiting for
    the last word before showing the first one makes the assistant feel slow
    even when it is not, so the page reads it out as it is written.

    Yields plain strings. Raises AIError before the first piece if the request
    cannot be made at all.
    """
    import groq

    client = _get_client()
    messages = _chat_messages(user_message, history=history, trip_context=trip_context)

    try:
        stream = client.chat.completions.create(
            model=settings.GROQ_CHAT_MODEL,
            max_tokens=2000,
            messages=messages,
            reasoning_effort=CHAT_REASONING_EFFORT,
            stream=True,
        )
    except groq.AuthenticationError as exc:
        raise AIError("The Groq API key is missing or invalid.") from exc
    except groq.RateLimitError as exc:
        raise AIError("Too many requests right now. Please try again in a moment.") from exc
    except groq.APITimeoutError as exc:
        raise AIError("The AI service took too long to answer. Please try again.") from exc
    except groq.APIConnectionError as exc:
        raise AIError("Could not reach the AI service. Check your internet connection.") from exc
    except groq.APIStatusError as exc:
        logger.warning("Groq stream error %s: %s", exc.status_code, exc)
        if exc.status_code == 404:
            raise AIError(
                "The configured AI model (%s) is not available on this API key."
                % settings.GROQ_CHAT_MODEL
            ) from exc
        raise AIError("The AI service returned an error. Please try again.") from exc

    cleaner = _ReasoningFilter()
    for event in stream:
        if not event.choices:
            continue
        piece = event.choices[0].delta.content
        if not piece:
            continue
        visible = cleaner.feed(piece)
        if visible:
            yield visible

    tail = cleaner.finish()
    if tail:
        yield tail


# ---------------------------------------------------------------------------
# 2. Translation (Telugu <-> English)
# ---------------------------------------------------------------------------
LANGUAGE_NAMES = {"en": "English", "te": "Telugu"}


def translate(text, source_lang="te", target_lang="en"):
    """Translate text between Telugu and English."""
    source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
    target_name = LANGUAGE_NAMES.get(target_lang, target_lang)

    system = (
        f"You are a translator between {source_name} and {target_name}. "
        f"Translate the user's text from {source_name} into {target_name}. "
        "Reply with ONLY the translation. No explanation, no quotes, no notes. "
        "Keep place names and numbers exactly as they are."
    )
    return _call(
        [{"role": "system", "content": system}, {"role": "user", "content": text}],
        max_tokens=1000,
        # Translating a sentence is not a problem that wants deliberation.
        reasoning_effort=CHAT_REASONING_EFFORT,
    )


# ---------------------------------------------------------------------------
# 3. Image recognition (vision)
# ---------------------------------------------------------------------------
VISION_MAX_EDGE = 768


def _shrink_for_vision(image_bytes, media_type="image/jpeg"):
    """
    Shrink a photo before sending it to the vision model.

    A phone camera produces something like 3024x4032. Every pixel of that is
    charged against the same per-minute token budget the answer has to come out
    of, and the model gains nothing from it - 768px on the long edge is more
    than enough to read a temple tower's shape and any signboard in the frame.
    It also makes the upload and the request noticeably quicker.

    Returns (bytes, media_type). The media type comes back with the bytes
    because shrinking re-encodes as JPEG: a PNG that went in still described as
    image/png would produce a data URI that disagrees with its own contents.

    If anything goes wrong - an unreadable file, no Pillow - the original bytes
    and type are returned untouched, because a slightly expensive request is
    much better than a failed one.
    """
    try:
        from io import BytesIO

        from PIL import Image

        image = Image.open(BytesIO(image_bytes))
        if max(image.size) <= VISION_MAX_EDGE:
            return image_bytes, media_type

        image = image.convert("RGB")
        image.thumbnail((VISION_MAX_EDGE, VISION_MAX_EDGE))
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue(), "image/jpeg"
    except Exception as exc:  # noqa: BLE001 - never fail a request over this
        logger.info("Could not shrink the image, sending it as it is: %s", exc)
        return image_bytes, media_type


def analyse_image(image_bytes, media_type="image/jpeg", question=""):
    """
    Send a photo to the vision model and ask what place it is.

    The picture is turned into base64 text (a way of writing binary data using
    only normal letters) so it can travel inside a normal web request.

    Returns (text, is_confident).
    """
    image_bytes, media_type = _shrink_for_vision(image_bytes, media_type)
    encoded = base64.standard_b64encode(image_bytes).decode("utf-8")
    prompt = question.strip() or "What place is this, and how can I visit it?"

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": IMAGE_SYSTEM_PROMPT + "\n\nQuestion: " + prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{encoded}"},
                },
            ],
        }
    ]

    # reasoning_effort="none" is the whole difference between this working and
    # not. Left to deliberate, the model argues itself out of the right answer:
    # on a photo of the Dwarkadhish Temple it spent thousands of tokens second
    # guessing a flag and settled on Kedarnath, then on a temple in Sri Lanka,
    # both with high confidence. With reasoning off it answered "Dwarkadhish
    # Temple, Dwarka, Gujarat" in nineteen tokens.
    #
    # It also fixes the budget. The free tier allows 8000 tokens PER MINUTE for
    # this model - prompt, image and reply together - so the old 4000-token
    # deliberations regularly hit the ceiling and returned nothing at all.
    text = _call(
        messages,
        model=settings.GROQ_VISION_MODEL,
        max_tokens=1500,
        reasoning_effort="none",
    )
    is_confident = "CONFIDENCE: HIGH" in text.upper()
    return text, is_confident


# ---------------------------------------------------------------------------
# 4. Speech to text (Whisper)
# ---------------------------------------------------------------------------
def transcribe(audio_bytes, filename="audio.webm", language=None):
    """
    Turn a recorded audio file into text using Whisper.

    This is the backup for browsers that cannot do speech recognition
    themselves. language is "en" or "te", or None to auto-detect.
    """
    import groq

    client = _get_client()
    try:
        result = client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model=settings.GROQ_WHISPER_MODEL,
            language=language or None,
        )
    except groq.AuthenticationError as exc:
        raise AIError("The Groq API key is missing or invalid.") from exc
    except groq.RateLimitError as exc:
        raise AIError("Too many requests right now. Please try again in a moment.") from exc
    except groq.APIConnectionError as exc:
        raise AIError("Could not reach the AI service. Check your internet connection.") from exc
    except groq.APIStatusError as exc:
        logger.warning("Whisper error %s: %s", exc.status_code, exc)
        raise AIError("Could not understand that recording. Please try again.") from exc

    text = (getattr(result, "text", "") or "").strip()
    if not text:
        raise AIError("No speech was found in that recording. Please try again.")
    return text


# ---------------------------------------------------------------------------
# 5. Itinerary help (AI version of the day-by-day plan)
# ---------------------------------------------------------------------------
def suggest_itinerary(trip_summary):
    """Ask the AI to improve or explain a trip plan we already calculated."""
    message = (
        "Here is a trip a customer has planned in our app. Give a short, "
        "friendly day-by-day suggestion and two or three practical tips "
        "(what to carry, best time of day for each place, what to watch out "
        "for). Remind them the costs are estimates.\n\n" + trip_summary
    )
    return _call(
        [
            {"role": "system", "content": TRAVEL_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        reasoning_effort=CHAT_REASONING_EFFORT,
    )
