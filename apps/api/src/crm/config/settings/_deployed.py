"""Shared hardening for deployed environments (staging/production).

These environments never read a ``.env`` file: every value must come from the
runtime (container env, secret manager). Required variables fail fast at boot.
"""

from .base import *  # noqa: F403
from .base import build_databases, env, env_list

DEBUG = False

SECRET_KEY = env("SECRET_KEY", required=True)
DATABASES = build_databases(env("DATABASE_URL", required=True))
REDIS_URL = env("REDIS_URL", required=True)
CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", REDIS_URL)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", required=True)
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", required=True)
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", required=True)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
