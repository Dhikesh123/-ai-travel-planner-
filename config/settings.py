"""
Django settings for the AI Travel Planner project.

Everything secret (passwords, API keys) is read from the .env file,
NEVER written directly in this file.
"""
import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# BASE_DIR is the folder that contains manage.py
BASE_DIR = Path(__file__).resolve().parent.parent

# Read the .env file and put its values into the environment
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    """Read a True/False value from the environment."""
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


# --- Security -------------------------------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key-change-me")

# Vercel sets this variable inside every deployment, so it tells us
# whether we are running on the live site or on this computer.
ON_VERCEL = bool(os.getenv("VERCEL"))

# Render sets its own marker the same way. The site is deployed to both, so
# each host is detected separately and "live" means either one.
ON_RENDER = bool(os.getenv("RENDER"))

ON_LIVE_SITE = ON_VERCEL or ON_RENDER

# Debug mode is helpful locally, but on a live site it shows visitors our
# settings and file paths, so it stays off there unless we ask for it.
DEBUG = env_bool("DEBUG", not ON_LIVE_SITE)

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()
]

# Add the Vercel addresses automatically, so a new deployment never fails
# with "DisallowedHost" just because an environment variable was forgotten.
if ON_VERCEL:
    # A leading dot means "this domain and any sub-domain of it".
    for host in (".vercel.app", os.getenv("VERCEL_URL", "").strip()):
        if host and host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)

# Render publishes the service's public address the same way, e.g.
# "ai-travel-planner.onrender.com". The loop below turns whatever lands in
# ALLOWED_HOSTS into a matching https origin, so CSRF is handled too.
if ON_RENDER:
    for host in (".onrender.com", os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()):
        if host and host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)

# Hosting platforms put a proxy in front of us and terminate HTTPS there.
# Django must be told, or it thinks every request is plain HTTP and the
# secure session/CSRF cookies are never accepted.
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# Forms only work if the address they were submitted from is trusted, so
# every allowed host gets a matching https origin.
for host in ALLOWED_HOSTS:
    if host in ("127.0.0.1", "localhost", "*"):
        continue
    origin = f"https://*{host}" if host.startswith(".") else f"https://{host}"
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Groq AI --------------------------------------------------------------
# One key, three models - each one is good at a different job.

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Chat and translation: fast and good with Indian languages
GROQ_CHAT_MODEL = os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")

# Image recognition: the model that can actually look at pictures
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")

# Speech to text: turns a recording into words
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")

# --- Applications ---------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    # Our app
    "travel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves CSS/JS in production. Must sit directly below SecurityMiddleware.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database -------------------------------------------------------------
# SQLite now. To move to PostgreSQL later, only this block changes.

DATABASES = {
    # Reads DATABASE_URL when the host provides one (Postgres in production),
    # and falls back to the local SQLite file when it is absent - so running
    # the site on this machine works exactly as it always has.
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# --- Password validation --------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalization -------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# --- Static and media files ----------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # WhiteNoise compresses the collected files and adds a content hash to
    # each name, so browsers can cache them forever and still see updates.
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

MEDIA_URL = "media/"

# On serverless hosts the project folder is read-only, so uploads must go
# somewhere writable. /tmp is the only writable place on Vercel.
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/tmp/media" if ON_VERCEL else BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Login / logout -------------------------------------------------------

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"

# --- File upload rules (used by our forms) --------------------------------

MAX_UPLOAD_SIZE_MB = 5
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".gif"]

# Reject huge uploads before they reach our code (Django-level guard)
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# --- Django REST Framework ------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# --- Extra security when DEBUG is off ------------------------------------

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"
