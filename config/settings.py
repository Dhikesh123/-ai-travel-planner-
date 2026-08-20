"""
Django settings for the AI Travel Planner project.

Everything secret (passwords, API keys) is read from the .env file,
NEVER written directly in this file.
"""
import os
import sys
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

# --- Cross-origin access for the Vercel frontend --------------------------
# The frontend is a static site on Vercel; this Django service is the API it
# calls. Because those are two different origins, the browser refuses the
# request unless the API says the origin is welcome.
#
# Only the /api/ paths are opened up, and only to origins we name - never
# CORS_ALLOW_ALL_ORIGINS, which would let any site on the internet read this
# API from a visitor's browser.

CORS_URLS_REGEX = r"^/api/.*$"

# The admin portal signs in and then reads staff-only data, which means the
# session cookie has to travel with its requests. Allowing credentials is only
# safe because the origins below are named individually - it would be
# dangerous combined with a wildcard.
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("FRONTEND_ORIGINS", "").split(",") if o.strip()
]

# Vercel gives every deployment its own hostname (preview builds included), so
# the project's own subdomains are matched by pattern rather than listed.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://ai-travel-planner-[a-z0-9-]+\.vercel\.app$",
]

# Local development: the frontend opened straight from a file or a simple
# static server still needs to reach a Django running on this machine.
if DEBUG:
    CORS_ALLOWED_ORIGINS += [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]

# A cross-origin login is still a form post as far as Django is concerned, so
# every origin allowed to call the API must also be trusted for CSRF.
CSRF_TRUSTED_ORIGINS += [o for o in CORS_ALLOWED_ORIGINS if o not in CSRF_TRUSTED_ORIGINS]
CSRF_TRUSTED_ORIGINS += ["https://*.vercel.app"]

# Browsers only attach a cookie to a cross-site request when it is marked
# SameSite=None, and they only accept that combination over HTTPS. Locally the
# site runs on plain http, so the stricter default is kept there instead.
if not DEBUG:
    SESSION_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SAMESITE = "None"

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
    # Issues the API tokens the admin portal signs in with. See the
    # authentication note in REST_FRAMEWORK below for why it is needed.
    "rest_framework.authtoken",
    "corsheaders",
    # Our app
    "travel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves CSS/JS in production. Must sit directly below SecurityMiddleware.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # Answers the browser's cross-origin checks for the Vercel frontend. It has
    # to run before CommonMiddleware so the CORS headers are attached even to
    # the replies CommonMiddleware short-circuits, such as redirects.
    "corsheaders.middleware.CorsMiddleware",
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
                # Supplies ASSET_V, the cache-buster on the CSS/JS URLs.
                "travel.context_processors.asset_version",
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
    # Keeping connections open between requests is a clear win on a long-lived
    # server like Render, but a serverless function cannot reuse them the same
    # way: every concurrent invocation holds its own, and a small Postgres
    # plan runs out of connection slots long before it runs out of anything
    # else. On Vercel the connection is therefore closed at the end of each
    # request, which matters even more when both hosts share one database.
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=0 if ON_VERCEL else 600,
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

# --- Email (used by "forgot password") ------------------------------------
#
# Password reset is only as good as its delivery: if the mail never arrives,
# the reset link never reaches the person locked out. So the backend is chosen
# by whether credentials actually exist, rather than assuming SMTP works.
#
#   EMAIL_HOST_USER + EMAIL_HOST_PASSWORD set  ->  real SMTP
#   either one missing                         ->  print to the console/logs
#
# The console fallback is deliberate. A misconfigured SMTP host raises at send
# time and turns "forgot password" into a 500; printing instead keeps the flow
# working and puts the link somewhere a developer can still reach it. Nothing
# is silently lost - the startup banner below says which mode is live.
#
# For Gmail this must be an App Password (16 characters, from Google Account ->
# Security -> App passwords), NOT the normal account password: Google has
# refused plain passwords for SMTP since 2022.

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "").replace(" ", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() != "false"
EMAIL_TIMEOUT = 20

EMAIL_IS_CONFIGURED = bool(EMAIL_HOST_USER and EMAIL_HOST_PASSWORD)

EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_IS_CONFIGURED
    else "django.core.mail.backends.console.EmailBackend"
)

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@ai-travel-planner.local"
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# How long a reset link stays valid. Three hours is long enough to find the
# mail and short enough that a forwarded inbox is not a standing key.
PASSWORD_RESET_TIMEOUT = 60 * 60 * 3

# --- File upload rules (used by our forms) --------------------------------

MAX_UPLOAD_SIZE_MB = 5
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".gif"]

# Reject huge uploads before they reach our code (Django-level guard)
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# --- Django REST Framework ------------------------------------------------

REST_FRAMEWORK = {
    # Two ways in, for two different callers:
    #
    # SessionAuthentication serves the Django site itself, where the browser
    # is on the same origin as the API and the cookie is first-party.
    #
    # TokenAuthentication serves the Vercel frontend. A cookie cannot be
    # relied on there: vercel.app and onrender.com are separate registrable
    # domains, so the session cookie is third-party, and browsers now block
    # those by default no matter what SameSite says. A token sent in the
    # Authorization header is not a cookie, so none of that applies.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
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


# Password hashing is deliberately slow - that is the point of PBKDF2 - but the
# test suite creates a user and logs in for all 63 tests, and that hashing was
# most of a run that took minutes. Tests do not need the real hasher to prove
# that login works, so under "manage.py test" only, use the cheap one.
if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
