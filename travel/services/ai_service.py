"""
Everything that talks to the Groq AI API lives here.

Why one file? So the API key is used in exactly ONE place. The rest of the
project just calls these functions. The key itself comes from the .env file
through Django settings, and is never sent to the browser.

Groq gives us four things, each with a model that suits the job:

  * chat and translation -> llama-3.3-70b-versatile  (fast, good at Indian
    languages including Telugu)
  * image recognition    -> qwen/qwen3.6-27b         (the vision model)
  * speech to text       -> whisper-large-v3         (audio to text)
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

Answer in exactly this shape:

CONFIDENCE: HIGH or LOW
PLACE: the name of the place, or "Not sure"
LOCATION: city, state, country, or "Not sure"
ABOUT: two or three sentences about the place
VISIT: how a traveller can get there and the best time to visit (estimates only)
NEARBY: two or three other places worth seeing close by

Rules:
- Use CONFIDENCE: LOW whenever you are not certain. It is much better to say
  you are not sure than to name the wrong monument.
- If the picture is not a place at all (a person, food, a document), say so in
  PLACE and keep CONFIDENCE: LOW.
- Never invent ticket prices, timings or booking details. Anything you say
  about cost or timing is a rough estimate and must be described that way.
- Give the final answer only. Do not show your reasoning.
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


def _get_client():
    """Create the Groq client. The import is inside the function so the site
    still runs even if the library is missing."""
    try:
        from groq import Groq
    except ImportError as exc:  # pragma: no cover
        raise AIError("The 'groq' package is not installed. Run: pip install groq") from exc

    if not is_configured():
        raise AIError(NO_KEY_MESSAGE)

    return Groq(api_key=settings.GROQ_API_KEY)


def _strip_reasoning(text):
    """
    Some models "think out loud" inside <think>...</think> tags before giving
    the real answer. The customer should only see the answer, so we remove
    those parts.
    """
    if not text:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # If the model ran out of room and never closed the tag, drop the opener
    # and everything after it, then fall back to the raw text if nothing is left.
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL).strip()
    return cleaned or text.strip()


def _call(messages, model=None, max_tokens=2000):
    """One place that actually sends the request and handles every error."""
    import groq

    client = _get_client()
    try:
        response = client.chat.completions.create(
            model=model or settings.GROQ_CHAT_MODEL,
            max_tokens=max_tokens,
            messages=messages,
        )
    except groq.AuthenticationError as exc:
        logger.warning("Groq auth failed: %s", exc)
        raise AIError("The Groq API key is missing or invalid.") from exc
    except groq.RateLimitError as exc:
        logger.warning("Groq rate limited: %s", exc)
        raise AIError("Too many requests right now. Please try again in a moment.") from exc
    except groq.APIConnectionError as exc:
        logger.warning("Groq connection error: %s", exc)
        raise AIError("Could not reach the AI service. Check your internet connection.") from exc
    except groq.APIStatusError as exc:
        logger.warning("Groq API error %s: %s", exc.status_code, exc)
        raise AIError("The AI service returned an error. Please try again.") from exc

    if not response.choices:
        raise AIError("The AI service sent an empty reply. Please try again.")

    text = _strip_reasoning(response.choices[0].message.content)
    if not text:
        raise AIError("The AI service sent an empty reply. Please try again.")
    return text


# ---------------------------------------------------------------------------
# 1. Chat
# ---------------------------------------------------------------------------
def chat(user_message, history=None, trip_context=""):
    """
    Send one customer message (plus recent history) to the AI.

    history = list of {"role": "user"/"assistant", "content": "..."}
    trip_context = optional text describing the trip the customer is viewing.
    """
    system = TRAVEL_SYSTEM_PROMPT
    if trip_context:
        system += f"\n\nThe customer is currently looking at this trip:\n{trip_context}"

    messages = [{"role": "system", "content": system}]
    for item in (history or [])[-10:]:  # keep the last 10 turns only
        if item.get("content"):
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": user_message})

    return _call(messages)


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
    )


# ---------------------------------------------------------------------------
# 3. Image recognition (vision)
# ---------------------------------------------------------------------------
def analyse_image(image_bytes, media_type="image/jpeg", question=""):
    """
    Send a photo to the vision model and ask what place it is.

    The picture is turned into base64 text (a way of writing binary data using
    only normal letters) so it can travel inside a normal web request.

    Returns (text, is_confident).
    """
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

    # The vision model reasons a lot before answering, so it needs plenty of
    # room. Too small a limit and it gets cut off mid-thought.
    text = _call(messages, model=settings.GROQ_VISION_MODEL, max_tokens=4000)
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
        ]
    )
