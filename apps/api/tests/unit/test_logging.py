import json
import logging

from crm.core.logging import JSONFormatter, sanitize
from crm.core.request_context import clear_request_context, set_request_context


def _make_record(message: str, **extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="crm.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_includes_structured_fields() -> None:
    set_request_context(request_id="req-1", correlation_id="corr-1")
    try:
        formatter = JSONFormatter(environment="test", service="api")
        payload = json.loads(formatter.format(_make_record("hello", event="unit.test")))
    finally:
        clear_request_context()

    assert payload["level"] == "info"
    assert payload["environment"] == "test"
    assert payload["service"] == "api"
    assert payload["request_id"] == "req-1"
    assert payload["correlation_id"] == "corr-1"
    assert payload["event"] == "unit.test"
    assert payload["message"] == "hello"
    assert "timestamp" in payload


def test_sanitize_redacts_sensitive_keys_recursively() -> None:
    raw = {
        "whatsapp_access_token": "secret-token",
        "Authorization": "Bearer abc",
        "X-Api-Key": "abc",
        "password": "hunter2",
        "nested": {"client_secret": "abc", "safe": "visible"},
        "items": [{"refresh_token": "abc"}],
        "organization_id": "org-1",
    }

    clean = sanitize(raw)

    assert clean["whatsapp_access_token"] == "[REDACTED]"
    assert clean["Authorization"] == "[REDACTED]"
    assert clean["X-Api-Key"] == "[REDACTED]"
    assert clean["password"] == "[REDACTED]"
    assert clean["nested"]["client_secret"] == "[REDACTED]"
    assert clean["nested"]["safe"] == "visible"
    assert clean["items"][0]["refresh_token"] == "[REDACTED]"
    assert clean["organization_id"] == "org-1"


def test_formatter_redacts_metadata() -> None:
    formatter = JSONFormatter(environment="test", service="api")
    record = _make_record("call done", metadata={"api_key": "abc", "latency_ms": 12})

    payload = json.loads(formatter.format(record))

    assert payload["metadata"] == {"api_key": "[REDACTED]", "latency_ms": 12}
