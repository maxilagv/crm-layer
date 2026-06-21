"""Test settings: deterministic, isolated, no external providers.

Tests run against PostgreSQL (Django creates a dedicated ``test_*`` database)
so that constraints like ``nulls_distinct`` and ``SELECT ... FOR UPDATE SKIP
LOCKED`` behave exactly as in production. Redis is replaced with fakeredis and
Celery runs eagerly in-process.
"""

from .base import *  # noqa: F403

APP_ENV = "test"
DEBUG = False
SECRET_KEY = "test-secret-key"  # noqa: S105 - deterministic test-only value
SIMPLE_JWT["SIGNING_KEY"] = "test-jwt-signing-key-at-least-32-bytes-long"  # noqa: F405
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

MIDDLEWARE = [
    middleware
    for middleware in MIDDLEWARE  # noqa: F405
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]

HEALTHCHECK_USE_FAKE_REDIS = True
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ai-crm-tests",
    }
}
LOGIN_RATE_LIMIT_ATTEMPTS = 3
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Never let tests reach real providers, even if the developer's .env leaks in.
OPENAI_API_KEY = ""
ANTHROPIC_API_KEY = ""
GOOGLE_PLACES_API_KEY = ""
PAGESPEED_API_KEY = ""
GOOGLE_CSE_API_KEY = ""
GOOGLE_CSE_CX = ""
APOLLO_API_KEY = ""
HUNTER_API_KEY = ""
RESEND_API_KEY = ""
DEFAULT_FROM_EMAIL = "soporte@weblayer.cloud"
PROSPECTING_EMAIL_DAILY_CAP = 50
WHATSAPP_ACCESS_TOKEN = ""
WHATSAPP_VERIFY_TOKEN = ""
WHATSAPP_APP_SECRET = ""
S3_ENDPOINT_URL = ""
S3_ACCESS_KEY_ID = ""
S3_SECRET_ACCESS_KEY = ""
S3_BUCKET_NAME = ""

LOGGING["formatters"]["json"]["environment"] = "test"  # noqa: F405
