"""
Extra values made available to every template.
"""
from pathlib import Path

from django.conf import settings

from . import languages as language_list


def _newest_static_mtime():
    """The modification time of the most recently changed CSS/JS file."""
    newest = 0.0
    for folder in getattr(settings, "STATICFILES_DIRS", []):
        for pattern in ("*.css", "*.js"):
            for path in Path(folder).rglob(pattern):
                try:
                    newest = max(newest, path.stat().st_mtime)
                except OSError:
                    continue  # a file that vanished mid-scan is not worth failing over
    return newest


def asset_version(request):
    """
    A value to hang on the end of CSS/JS URLs so a browser never serves a
    stale copy after an edit.

    In development it is the newest static file's timestamp, so editing any
    CSS or JS changes the URL and the browser fetches the new file by itself -
    no hard refresh needed. Rescanning the folder on every request is only
    acceptable because DEBUG is a handful of local files.

    In production the URLs already carry a content hash from
    ManifestStaticFilesStorage, so a fixed value is enough and the folder is
    never scanned.
    """
    if settings.DEBUG:
        return {"ASSET_V": str(int(_newest_static_mtime()))}
    return {"ASSET_V": "1"}


def languages(request):
    """
    The languages the site speaks, for the dropdowns and for the browser.

    SUPPORTED_LANGUAGES is looped over in the templates. LANGUAGE_DATA is the
    same list as plain dictionaries, which base.html writes into the page as
    JSON so speech.js and chatbot.js work from it too - before this, each
    JavaScript file carried its own idea of which alphabets existed.
    """
    return {
        "SUPPORTED_LANGUAGES": language_list.LANGUAGES,
        "LANGUAGE_DATA": language_list.as_dicts(),
        "DEFAULT_LANGUAGE": language_list.DEFAULT_CODE,
    }
