"""Shared Django settings.

Environment-specific modules (local/test/staging/production) import from this
module and override what they need. Secrets always come from environment
variables; `.env` loading is a local-only convenience handled by `local.py`.
"""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from corsheaders.defaults import default_headers


def env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "", *, required: bool = False) -> list[str]:
    raw_value = env(name, default, required=required)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def build_databases(database_url: str) -> dict:
    return {
        "default": dj_database_url.parse(
            database_url,
            conn_max_age=int(env("DATABASE_CONN_MAX_AGE", "60")),
            conn_health_checks=True,
        )
    }


# apps/api/src/crm/config/settings/base.py -> apps/api
BASE_DIR = Path(__file__).resolve().parents[4]

APP_ENV = env("APP_ENV", "local")
SERVICE_NAME = env("SERVICE_NAME", "api")
APP_VERSION = env("APP_VERSION", "0.1.0")
GIT_COMMIT = env("GIT_COMMIT", "unknown")
BUILD_DATE = env("BUILD_DATE", "unknown")
PUBLIC_APP_URL = env("PUBLIC_APP_URL", "http://localhost:3000")

# No fallback here on purpose: environments must provide SECRET_KEY (local and
# test set safe development values). Django fails closed if it stays empty.
SECRET_KEY = env("SECRET_KEY")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,api")

INSTALLED_APPS = [
    "crm.accounts",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "pgvector.django",
    "crm.core",
    "crm.organizations",
    "crm.business_settings",
    "crm.contacts",
    "crm.conversations",
    "crm.whatsapp",
    "crm.ai",
    "crm.leads",
    "crm.sales",
    "crm.notifications",
    "crm.tasks",
    "crm.automations",
    "crm.media",
    "crm.clients",
    "crm.support",
    "crm.documents",
    "crm.prospecting",
    "crm.integrations",
    "crm.analytics",
    "crm.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "crm.core.middleware.RequestIDMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "crm.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "crm.config.wsgi.application"
ASGI_APPLICATION = "crm.config.asgi.application"

DATABASE_URL = env("DATABASE_URL", "postgres://ai_crm:ai_crm@localhost:5432/ai_crm")
DATABASES = build_databases(DATABASE_URL)
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-ar"
TIME_ZONE = env("TIME_ZONE", "America/Argentina/Buenos_Aires")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_HEADERS = (*default_headers, "x-organization-id")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "crm.accounts.authentication.APIKeyAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Secure by default: public endpoints (health, schema) opt in to AllowAny.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "crm.core.api.pagination.StandardPagination",
    "PAGE_SIZE": int(env("API_DEFAULT_PAGE_SIZE", "50")),
    "EXCEPTION_HANDLER": "crm.core.api.exceptions.enveloped_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": env_bool("JWT_ROTATE_REFRESH_TOKENS", True),
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
}
JWT_SIGNING_KEY = env("JWT_SIGNING_KEY")
if JWT_SIGNING_KEY:
    SIMPLE_JWT["SIGNING_KEY"] = JWT_SIGNING_KEY

REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("CACHE_URL", REDIS_URL),
    }
}

LOGIN_RATE_LIMIT_ATTEMPTS = int(env("LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(env("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))

SPECTACULAR_SETTINGS = {
    "TITLE": "AI CRM API",
    "DESCRIPTION": "Private operational CRM backend API.",
    "VERSION": APP_VERSION,
    "SERVE_INCLUDE_SCHEMA": False,
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = int(env("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))
CELERY_TASK_TIME_LIMIT = int(env("CELERY_TASK_TIME_LIMIT", "300"))
CELERY_TASK_SOFT_TIME_LIMIT = int(env("CELERY_TASK_SOFT_TIME_LIMIT", "240"))
CELERY_RESULT_EXPIRES = int(env("CELERY_RESULT_EXPIRES", "86400"))
CELERY_BEAT_SCHEDULE = {
    "process-outbox": {
        "task": "crm.core.tasks.process_outbox",
        "schedule": float(env("OUTBOX_PROCESS_INTERVAL_SECONDS", "60")),
    },
    "tasks-send-due-reminders": {
        "task": "tasks.send_due_reminders",
        "schedule": float(env("TASK_REMINDER_INTERVAL_SECONDS", "60")),
    },
    "tasks-escalate-overdue": {
        "task": "tasks.escalate_overdue_tasks",
        "schedule": float(env("TASK_ESCALATION_INTERVAL_SECONDS", "300")),
    },
    "notifications-build-daily-digest": {
        "task": "notifications.build_daily_digest",
        "schedule": float(env("NOTIFICATION_DIGEST_INTERVAL_SECONDS", "86400")),
    },
    "observability-check-system-health": {
        "task": "observability.check_system_health",
        "schedule": float(env("OBSERVABILITY_HEALTH_INTERVAL_SECONDS", "300")),
    },
    "prospecting-run-followups": {
        "task": "prospecting.run_followups",
        "schedule": float(env("PROSPECTING_FOLLOWUP_INTERVAL_SECONDS", "21600")),
    },
    "prospecting-send-due-emails": {
        "task": "prospecting.send_due_emails",
        "schedule": float(env("PROSPECTING_EMAIL_SEND_INTERVAL_SECONDS", "300")),
    },
}
# AI workloads run on dedicated queues so an image render or a long audio never
# blocks a hot sales reply.
CELERY_TASK_ROUTES = {
    "ai.generate_sales_reply": {"queue": "ai_fast"},
    "ai.generate_support_reply": {"queue": "ai_fast"},
    "ai.score_lead": {"queue": "ai_fast"},
    "ai.extract_tasks": {"queue": "ai_fast"},
    "ai.classify_risk": {"queue": "ai_fast"},
    "ai.summarize_conversation": {"queue": "ai_slow"},
    "ai.transcribe_audio": {"queue": "transcription"},
    "ai.extract_ticket_from_audio": {"queue": "transcription"},
    "ai.generate_image": {"queue": "image_generation"},
    "ai.create_embeddings": {"queue": "embeddings"},
    "ai.run_eval_suite": {"queue": "evals"},
    "ai.cleanup_old_runs": {"queue": "ai_slow"},
    "ai.recalculate_usage": {"queue": "ai_slow"},
    # Phase 7: media + support. Audio/transcription on their own queue, image
    # generation isolated so it never blocks a hot support reply.
    "media.download_whatsapp_media": {"queue": "transcription"},
    "media.process_audio": {"queue": "transcription"},
    "media.transcribe_audio": {"queue": "transcription"},
    "media.generate_image": {"queue": "image_generation"},
    "media.store_generated_image": {"queue": "image_generation"},
    "media.cleanup_failed_jobs": {"queue": "ai_slow"},
    "support.create_ticket_from_audio": {"queue": "transcription"},
    "support.triage_ticket": {"queue": "ai_fast"},
    "support.generate_support_reply": {"queue": "ai_fast"},
    "support.notify_owner_for_urgent_ticket": {"queue": "ai_fast"},
    "tasks.extract_tasks_from_message": {"queue": "operations"},
    "tasks.send_due_reminders": {"queue": "operations"},
    "tasks.escalate_overdue_tasks": {"queue": "operations"},
    "tasks.parse_owner_command": {"queue": "operations"},
    "notifications.send_notification": {"queue": "notifications"},
    "notifications.retry_failed_delivery": {"queue": "notifications"},
    "notifications.build_daily_digest": {"queue": "notifications"},
    "automations.dispatch_trigger": {"queue": "automations"},
    "automations.execute_rule": {"queue": "automations"},
    "automations.execute_action": {"queue": "automations"},
    "analytics.collect_daily_metrics": {"queue": "analytics"},
    "analytics.build_dashboard_snapshot": {"queue": "analytics"},
    "analytics.calculate_ai_costs": {"queue": "analytics"},
    "analytics.check_alerts": {"queue": "analytics"},
    "audit.compact_old_logs": {"queue": "analytics"},
    "observability.check_system_health": {"queue": "monitoring"},
    "prospecting.discover_batch": {"queue": "ai_slow"},
    "prospecting.enrich_prospect": {"queue": "ai_slow"},
    "prospecting.qualify_prospect": {"queue": "ai_fast"},
    "prospecting.run_outreach": {"queue": "ai_fast"},
    "prospecting.run_followups": {"queue": "ai_slow"},
    "prospecting.send_due_emails": {"queue": "notifications"},
    "prospecting.interpret_reply": {"queue": "ai_fast"},
}

OUTBOX_MAX_ATTEMPTS = int(env("OUTBOX_MAX_ATTEMPTS", "5"))
OUTBOX_STALE_LOCK_SECONDS = int(env("OUTBOX_STALE_LOCK_SECONDS", "300"))

HEALTHCHECK_REDIS_TIMEOUT_SECONDS = float(env("HEALTHCHECK_REDIS_TIMEOUT_SECONDS", "1.0"))
HEALTHCHECK_USE_FAKE_REDIS = env_bool("HEALTHCHECK_USE_FAKE_REDIS", False)

OPENAI_API_KEY = env("OPENAI_API_KEY")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
GEMINI_API_KEY = env("GEMINI_API_KEY")
# Google Places API (Cazador / autonomous sales agent prospect discovery).
GOOGLE_PLACES_API_KEY = env("GOOGLE_PLACES_API_KEY")
# PageSpeed Insights (website performance signal for the investigator).
PAGESPEED_API_KEY = env("PAGESPEED_API_KEY")
# Google Programmable Search (web search to find a prospect's site/socials). Needs key + cx.
GOOGLE_CSE_API_KEY = env("GOOGLE_CSE_API_KEY")
GOOGLE_CSE_CX = env("GOOGLE_CSE_CX")
GOOGLE_CSE_DAILY_CAP = int(env("GOOGLE_CSE_DAILY_CAP", "90"))
# Prospect data providers (B2B discovery + email finding).
APOLLO_API_KEY = env("APOLLO_API_KEY")
APOLLO_DAILY_CAP = int(env("APOLLO_DAILY_CAP", "50"))
APOLLO_MONTHLY_CAP = int(env("APOLLO_MONTHLY_CAP", "500"))
HUNTER_API_KEY = env("HUNTER_API_KEY")
HUNTER_MONTHLY_CAP = int(env("HUNTER_MONTHLY_CAP", "40"))
RESEND_API_KEY = env("RESEND_API_KEY")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "soporte@weblayer.cloud")
PROSPECTING_EMAIL_DAILY_CAP = int(env("PROSPECTING_EMAIL_DAILY_CAP", "50"))
PROSPECTING_EMAIL_FOOTER_ADDRESS = env(
    "PROSPECTING_EMAIL_FOOTER_ADDRESS",
    "WebLayer, Buenos Aires, Argentina",
)
WHATSAPP_ACCESS_TOKEN = env("WHATSAPP_ACCESS_TOKEN")
# Unofficial WhatsApp bridge (whatsapp-web.js) — temporary, for local testing.
WA_BRIDGE_SHARED_SECRET = env("WA_BRIDGE_SHARED_SECRET", "dev-bridge-secret")
WA_BRIDGE_URL = env("WA_BRIDGE_URL", "http://localhost:8787")
# Owner's WhatsApp number — owner detection, urgent-ticket alerts, reminder delivery.
OWNER_WHATSAPP_NUMBER = env("OWNER_WHATSAPP_NUMBER")
WHATSAPP_VERIFY_TOKEN = env("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_APP_SECRET = env("WHATSAPP_APP_SECRET")
WHATSAPP_GRAPH_API_VERSION = env("WHATSAPP_GRAPH_API_VERSION", "v23.0")
WHATSAPP_API_BASE_URL = env("WHATSAPP_API_BASE_URL", "https://graph.facebook.com")
WHATSAPP_REQUEST_TIMEOUT_SECONDS = float(env("WHATSAPP_REQUEST_TIMEOUT_SECONDS", "10"))
WHATSAPP_MEDIA_DOWNLOAD_TIMEOUT_SECONDS = float(
    env("WHATSAPP_MEDIA_DOWNLOAD_TIMEOUT_SECONDS", "30")
)
S3_ENDPOINT_URL = env("S3_ENDPOINT_URL")
S3_REGION = env("S3_REGION")
S3_ACCESS_KEY_ID = env("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = env("S3_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = env("S3_BUCKET_NAME")
MEDIA_PRIVATE_ROOT = env("MEDIA_PRIVATE_ROOT", str(BASE_DIR / "private_media"))
MEDIA_STORAGE_PROVIDER = env("MEDIA_STORAGE_PROVIDER", "local")

LOG_LEVEL = env("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "sensitive_data": {"()": "crm.core.logging.SensitiveDataFilter"},
    },
    "formatters": {
        "json": {
            "()": "crm.core.logging.JSONFormatter",
            "environment": APP_ENV,
            "service": SERVICE_NAME,
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["sensitive_data"],
        }
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "celery": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "crm": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}
