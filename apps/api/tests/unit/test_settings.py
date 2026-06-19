"""Guard rails: the test environment must be isolated and deterministic."""

from django.conf import settings


def test_test_settings_are_active() -> None:
    assert settings.APP_ENV == "test"
    assert settings.DEBUG is False


def test_tests_run_against_postgres() -> None:
    # Constraints like nulls_distinct and SKIP LOCKED only behave like
    # production on PostgreSQL; tests must never silently fall back to SQLite.
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"


def test_celery_runs_eagerly_in_tests() -> None:
    assert settings.CELERY_TASK_ALWAYS_EAGER is True
    assert settings.CELERY_TASK_EAGER_PROPAGATES is True


def test_external_providers_are_disabled() -> None:
    assert settings.HEALTHCHECK_USE_FAKE_REDIS is True
    assert settings.OPENAI_API_KEY == ""
    assert settings.ANTHROPIC_API_KEY == ""
    assert settings.WHATSAPP_ACCESS_TOKEN == ""
    assert settings.S3_SECRET_ACCESS_KEY == ""
