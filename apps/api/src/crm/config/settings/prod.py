"""Production settings for the single-VPS deployment.

This module is intentionally fail-fast: missing or weak secrets abort startup
before Django, Celery, or the WhatsApp bridge can process traffic.
"""

from ._deployed import *  # noqa: F403
from .base import env, env_bool


def _require_min_length(name: str, value: str, minimum: int) -> str:
    if len(value.encode("utf-8")) < minimum:
        raise RuntimeError(f"{name} must be at least {minimum} bytes long in production")
    return value


def _reject_wildcards(name: str, values: list[str]) -> list[str]:
    if any(item.strip() == "*" for item in values):
        raise RuntimeError(f"{name} cannot contain '*' in production")
    return values


APP_ENV = "production"
DEBUG = False

if env_bool("DEBUG", False):
    raise RuntimeError("DEBUG must be false in production")

SECRET_KEY = _require_min_length("SECRET_KEY", env("SECRET_KEY", required=True), 50)
JWT_SIGNING_KEY = _require_min_length(
    "JWT_SIGNING_KEY",
    env("JWT_SIGNING_KEY", required=True),
    32,
)
WA_BRIDGE_SHARED_SECRET = _require_min_length(
    "WA_BRIDGE_SHARED_SECRET",
    env("WA_BRIDGE_SHARED_SECRET", required=True),
    32,
)
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": JWT_SIGNING_KEY}  # noqa: F405

ALLOWED_HOSTS = _reject_wildcards("ALLOWED_HOSTS", ALLOWED_HOSTS)  # noqa: F405
CORS_ALLOWED_ORIGINS = _reject_wildcards(  # noqa: F405
    "CORS_ALLOWED_ORIGINS",
    CORS_ALLOWED_ORIGINS,  # noqa: F405
)
CSRF_TRUSTED_ORIGINS = _reject_wildcards(  # noqa: F405
    "CSRF_TRUSTED_ORIGINS",
    CSRF_TRUSTED_ORIGINS,  # noqa: F405
)
CORS_ALLOW_ALL_ORIGINS = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

DATABASES["default"]["CONN_MAX_AGE"] = int(env("DATABASE_CONN_MAX_AGE", "60"))  # noqa: F405
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405

REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("DRF_ANON_THROTTLE_RATE", "60/minute"),
        "user": env("DRF_USER_THROTTLE_RATE", "600/minute"),
        "login": env("DRF_LOGIN_THROTTLE_RATE", "10/minute"),
        "prospecting": env("DRF_PROSPECTING_THROTTLE_RATE", "20/hour"),
    },
}

# OpenAPI schema naming warnings are tracked separately; keep deploy checks focused
# on production safety and runtime configuration.
SILENCED_SYSTEM_CHECKS = [
    "drf_spectacular.W001",
    "drf_spectacular.W002",
]

LOG_LEVEL = env("LOG_LEVEL", "INFO")
LOGGING["formatters"]["json"]["environment"] = APP_ENV  # noqa: F405
LOGGING["root"]["level"] = LOG_LEVEL  # noqa: F405
LOGGING["loggers"]["django"]["level"] = LOG_LEVEL  # noqa: F405
LOGGING["loggers"]["celery"]["level"] = LOG_LEVEL  # noqa: F405
LOGGING["loggers"]["crm"]["level"] = LOG_LEVEL  # noqa: F405

SENTRY_DSN = env("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        send_default_pii=False,
        environment=APP_ENV,
        release=APP_VERSION,  # noqa: F405
        traces_sample_rate=float(env("SENTRY_TRACES_SAMPLE_RATE", "0")),
    )
