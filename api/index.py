"""
Vercel serverless entry point.

Vercel's Python runtime imports this file and looks for a module-level
variable called `app` that is a WSGI application. Everything else about
the project is unchanged - this is just the doorway.

Locally you still use `python manage.py runserver`; this file is only
used when Vercel runs the site.
"""
import os
import sys
from pathlib import Path

# The function runs with api/ as the entry point, so the project root
# (the folder holding manage.py) has to be on the import path before
# "config.settings" can be found.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
