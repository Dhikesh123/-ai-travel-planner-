"""
Extra values made available to every template.
"""
from pathlib import Path

from django.conf import settings


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
