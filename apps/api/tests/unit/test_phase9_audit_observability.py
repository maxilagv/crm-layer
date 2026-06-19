from types import SimpleNamespace

import pytest

from crm.ai.services.ai_run_logger import AIRunLogger
from crm.audit.models import (
    AuditAIDecision,
    AuditLog,
    AuditSecurityEvent,
)
from crm.audit.services import (
    AIDecisionLogger,
    AuditLogger,
    ExternalRequestLogger,
    audit_event_create,
)
from crm.core.observability import celery as celery_observability
from crm.core.observability.context import (
    clear_request_context,
    get_correlation_id,
    get_request_id,
    set_request_context,
)
from crm.core.observability.metrics import MetricsRecorder
from tests.factories.accounts import UserFactory
from tests.factories.ai import AIRunFactory
from tests.factories.organizations import OrganizationFactory


@pytest.mark.django_db
def test_audit_log_before_after_sanitized() -> None:
    organization = OrganizationFactory()
    user = UserFactory()
    set_request_context(request_id="req-1", correlation_id="corr-1")

    AuditLogger.log(
        action="settings_updated",
        organization=organization,
        actor=user,
        resource_type="settings",
        resource_id="ai",
        before={"api_key": "sk-old", "temperature": "0.2"},
        after={"api_key": "sk-new", "temperature": "0.4"},
    )

    log = AuditLog.objects.get()
    assert log.before["api_key"] == "[REDACTED]"
    assert log.after["api_key"] == "[REDACTED]"
    assert log.request_id == "req-1"
    assert log.correlation_id == "corr-1"
    clear_request_context()


@pytest.mark.django_db
def test_audit_event_create_mirrors_security_event() -> None:
    organization = OrganizationFactory()
    user = UserFactory()

    audit_event_create(
        event_type="permission_denied",
        organization=organization,
        actor=user,
        metadata={"permission": "settings.manage", "token": "secret-token"},
    )

    assert AuditLog.objects.filter(action="permission_denied").exists()
    event = AuditSecurityEvent.objects.get(event_type="permission_denied")
    assert event.metadata["token"] == "[REDACTED]"
    assert event.severity == "medium"


@pytest.mark.django_db
def test_audit_ai_decision_from_ai_run() -> None:
    run = AIRunFactory(output_json={"reply": "Hola", "confidence": 0.75})

    decision = AIDecisionLogger.log_from_run(ai_run=run)

    assert decision.ai_run_id == run.id
    assert decision.provider == "fake"
    assert decision.decision["reply"] == "Hola"


@pytest.mark.django_db
def test_airun_finish_persists_ai_decision() -> None:
    run = AIRunFactory(output_json={"reply": "Listo", "confidence": 0.88})

    AIRunLogger.finish(run, status="success")

    assert AuditAIDecision.objects.filter(ai_run_id=run.id, decision_type=run.purpose).exists()


@pytest.mark.django_db
def test_external_request_logger_sanitizes_url_headers_and_error() -> None:
    organization = OrganizationFactory()

    record = ExternalRequestLogger.log(
        organization=organization,
        provider="openai",
        service="ai",
        operation="chat",
        method="post",
        url="https://api.example.test/v1/chat?access_token=secret&ok=1",
        status_code=500,
        success=False,
        error_message="failed token=secret-value",
        request_metadata={"headers": {"Authorization": "Bearer secret"}},
    )

    assert record.url_path == "/v1/chat?access_token=%5BREDACTED%5D&ok=1"
    assert record.error_message == "failed token=[REDACTED]"
    assert record.request_metadata["headers"]["Authorization"] == "[REDACTED]"


def test_metrics_recorder_increment() -> None:
    MetricsRecorder.reset()

    MetricsRecorder.increment("ai_runs_total", provider="fake")

    assert MetricsRecorder.snapshot()["counters"]["ai_runs_total|provider=fake"] == "1"


def test_celery_context_propagation() -> None:
    set_request_context(request_id="req-celery", correlation_id="corr-celery")
    headers = {}

    celery_observability.inject_context(headers=headers)
    clear_request_context()
    celery_observability.restore_context(
        task=SimpleNamespace(request=SimpleNamespace(headers=headers))
    )

    assert get_request_id() == "req-celery"
    assert get_correlation_id() == "corr-celery"
    clear_request_context()
