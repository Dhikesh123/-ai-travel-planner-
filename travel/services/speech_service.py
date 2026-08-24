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
