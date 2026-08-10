"""
Speech helpers.

Listening and speaking normally happen in the BROWSER using the Web Speech
API (see static/js/speech.js) - that is free, instant, and needs no server.

If the browser cannot do it (Safari, older phones, Firefox), the app falls
back to this file, which sends the recording to Whisper on the server.

This file also holds the language settings, so there is one place to change
them, and the Telugu detection used across the project.
"""
from .ai_service import AIError, transcribe, translate

# Codes the Web Speech API understands
SPEECH_LANGUAGES = {
    "en": {"recognition": "en-IN", "synthesis": "en-IN", "label": "English"},
    "te": {"recognition": "te-IN", "synthesis": "te-IN", "label": "Telugu"},
}


def detect_language(text):
    """
    Very simple language check: if the text contains Telugu letters, it is
    Telugu. Telugu characters live in the Unicode block 0C00-0C7F.
    """
    for char in text or "":
        if "ఀ" <= char <= "౿":
            return "te"
    return "en"


def to_english(text):
    """Translate to English only if the text is not already English."""
    if detect_language(text) == "en":
        return text, False
    return translate(text, source_lang="te", target_lang="en"), True


def to_telugu(text):
    """Translate English text into Telugu."""
    if detect_language(text) == "te":
        return text, False
    return translate(text, source_lang="en", target_lang="te"), True


def transcribe_audio(audio_bytes, language="en", filename="recording.webm"):
    """
    Turn a recording into text using Whisper on the server.

    Used by /api/transcribe/ when the browser has no speech recognition of
    its own. Pass language "en" or "te", or None to let Whisper guess.
    """
    return transcribe(audio_bytes, filename=filename, language=language)
