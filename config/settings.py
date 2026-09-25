import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-dev-key")
DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "corsheaders",
    "django_filters",
    "users",
    "chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

import os
from urllib.parse import urlparse

# --- PostgreSQL через DATABASE_URL (Railway/Render) либо отдельные поля ---
_database_url = os.getenv("DATABASE_URL")
if _database_url:
    _db = urlparse(_database_url)
    _DB_CONFIG = {
        "NAME": _db.path[1:],
        "USER": _db.username,
        "PASSWORD": _db.password,
        "HOST": _db.hostname,
        "PORT": _db.port or 5432,
        "OPTIONS": {"sslmode": "require"},
    }
else:
    _DB_CONFIG = {
        "NAME": os.getenv("DATABASE_NAME", "jwchat"),
        "USER": os.getenv("DATABASE_USER", "jwchat"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", "jwchat_secret"),
        "HOST": os.getenv("DATABASE_HOST", "localhost"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
    }

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        **_DB_CONFIG,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"

# Redis через REDIS_URL (Railway/Render) либо отдельные поля
_redis_url = os.getenv("REDIS_URL")
if _redis_url:
    _REDIS_HOSTS = [_redis_url]
else:
    _REDIS_HOSTS = [
        (
            os.getenv("REDIS_HOST", "127.0.0.1"),
            int(os.getenv("REDIS_PORT", "6379")),
        )
    ]

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": _REDIS_HOSTS,
        },
    },
}

CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

# Trust proxy headers (Railway/Render) for HTTPS
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cross-site auth: frontend (Vercel) and backend (Railway/Render) are different domains.
# SameSite=None + Secure is required so the session cookie survives HTTPS requests and WS handshakes.
# Overridable via env for same-site/plain-HTTP deployments (e.g. test on a bare IP without TLS).
_secure_cookies_default = not DEBUG
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "None" if _secure_cookies_default else "Lax")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", str(_secure_cookies_default)).strip() != "False"
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "None" if _secure_cookies_default else "Lax")
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", str(_secure_cookies_default)).strip() != "False"

# --- Uploads: не в память, файлы >2.5MB сразу на диск (частично в память не тянем) ---
FILE_UPLOAD_MAX_MEMORY_SIZE = 2_500_000
DATA_UPLOAD_MAX_MEMORY_SIZE = 15_000_000
FILE_UPLOAD_MAX_SIZE = int(os.getenv("FILE_UPLOAD_MAX_SIZE", str(100 * 1024 * 1024)))

# --- AI Assistant (GigaChat — бесплатный для разработчиков) ---
AI_ASSISTANT_USERNAME = os.getenv("AI_ASSISTANT_USERNAME", "AI Assistant")
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID", "")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET", "")
GIGACHAT_USERNAME = os.getenv("GIGACHAT_USERNAME", "")
GIGACHAT_PASSWORD = os.getenv("GIGACHAT_PASSWORD", "")
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat-Pro:latest")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
GIGACHAT_AUTH_URL = os.getenv("GIGACHAT_AUTH_URL", "https://ngw.devices.sberbank.ru:9443/api/v2/oauth")
GIGACHAT_BASE_URL = os.getenv("GIGACHAT_BASE_URL", "https://gigachat.devices.sberbank.ru/api/v1")
GIGACHAT_VERIFY_SSL = os.getenv("GIGACHAT_VERIFY_SSL", "False").strip().lower() == "true"
AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))
AI_CONTEXT_MESSAGES = int(os.getenv("AI_CONTEXT_MESSAGES", "20"))

# --- Email: восстановление пароля через Resend (транзакционные письма) ---
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
RESEND_FROM_NAME = os.getenv("RESEND_FROM_NAME", "JW CHAT")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}
