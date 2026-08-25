"""
Speech helpers.

Listening and speaking normally happen in the BROWSER using the Web Speech
API (see static/js/speech.js) - that is free, instant, and needs no server.

If the browser cannot do it (Safari, older phones, Firefox), the app falls
back to this file, which sends the recording to Whisper on the server.

Which languages exist is not decided here: that lives in travel/languages.py,
and this file reads it. Add a language there and the microphone, the
transcriber and the translator all pick it up.
"""
from .. import languages
from .ai_service import AIError, transcribe, translate

# Codes the Web Speech API understands, built from the one list.
SPEECH_LANGUAGES = {
    language.code: {
        "recognition": language.speech_code,
        "synthesis": language.speech_code,
        "label": language.label,
    }
    for language in languages.LANGUAGES
}


def detect_language(text):
    """
    Work out which language a piece of text is written in, by its alphabet.

    See languages.detect for what this can and cannot tell apart - the short
    version is that Hindi and Marathi share an alphabet, so Devanagari text
    is reported as Hindi.
    """
    return languages.detect(text)


def to_language(text, target_code):
    """
    Translate text into the target language, unless it is already in it.

    Returns (text, was_translated) so a caller can tell the customer whether
    anything actually happened.
    """
    source_code = detect_language(text)
    if source_code == languages.clean_code(target_code):
        return text, False
    return translate(text, source_lang=source_code, target_lang=target_code), True


def transcribe_audio(audio_bytes, language="en", filename="recording.webm"):
    """
    Turn a recording into text using Whisper on the server.

    Used by /api/transcribe/ when the browser has no speech recognition of
    its own. Pass any supported language code, or None to let Whisper guess.
    """
    return transcribe(audio_bytes, filename=filename, language=language)

# ---------------------------------------------------------------------------
# Speaking, when the browser cannot
# ---------------------------------------------------------------------------
# Reading text aloud normally happens in the browser, free and instantly.
# But a browser can only speak a language the operating system has a voice
# for, and Windows ships none for Telugu - so on most machines in India the
# "read aloud" button on a Telugu answer could do nothing but apologise.
#
# Microsoft's Edge read-aloud service has Telugu voices and needs no API key,
# so the server fetches the audio and hands it back as an mp3. It is only
# used when the browser has already said it cannot do the job itself.
VOICES = {
    "te": "te-IN-MohanNeural",
    "en": "en-IN-PrabhatNeural",
}
DEFAULT_VOICE = "en-IN-PrabhatNeural"

# Long enough for an AI answer, short enough that nobody can use this as a
# free audiobook service.
MAX_SPOKEN_CHARACTERS = 3000


def synthesize(text, language="en"):
    """
    Turn text into mp3 bytes in the given language.

    Raises AIError with something sayable if the speech service cannot be
    reached, so the page can explain rather than fail silently.
    """
    import asyncio

    import edge_tts

    text = (text or "").strip()[:MAX_SPOKEN_CHARACTERS]
    if not text:
        raise AIError("There is nothing to read aloud.")

    voice = VOICES.get(languages.clean_code(language), DEFAULT_VOICE)

    async def collect():
        audio = bytearray()
        async for chunk in edge_tts.Communicate(text, voice).stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        return bytes(audio)

    try:
        # A fresh loop each call: Django's request thread has none of its own,
        # and asyncio.run tidies it up afterwards.
        audio = asyncio.run(collect())
    except Exception as exc:                       # network, service, anything
        raise AIError(
            "The speech service could not be reached. The text is still on screen."
        ) from exc

    if not audio:
        raise AIError("The speech service returned nothing to play.")
    return audio
