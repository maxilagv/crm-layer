import pytest
from django.test import override_settings

from crm.prospecting.services.resend_client import ResendEmailClient, ResendEmailError


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


@override_settings(RESEND_API_KEY="rk_test", DEFAULT_FROM_EMAIL="soporte@weblayer.cloud")
def test_resend_client_send_parses_success():
    calls = []

    def fetcher(url, payload, headers, timeout):
        calls.append((url, payload, headers, timeout))
        return {"id": "email_123"}

    result = ResendEmailClient(fetcher=fetcher).send(
        to_email="owner@example.com",
        subject="Hola",
        body="Mensaje",
        headers={"List-Unsubscribe": "<https://example.com/u>"},
    )

    assert result["sent"] is True
    assert result["message_id"] == "email_123"
    assert calls[0][1]["to"] == ["owner@example.com"]
    assert calls[0][2]["Authorization"] == "Bearer rk_test"


def test_resend_client_empty_input_noops_without_fetch():
    def fetcher(*args, **kwargs):
        pytest.fail("fetcher should not be called")

    result = ResendEmailClient(api_key="", fetcher=fetcher).send(
        to_email="",
        subject="",
        body="",
    )

    assert result["sent"] is False
    assert result["error"] == "missing_required_input"


@override_settings(RESEND_API_KEY="rk_test", DEFAULT_FROM_EMAIL="soporte@weblayer.cloud")
def test_resend_client_429_returns_failed_result_without_raise():
    def fetcher(url, payload, headers, timeout):
        return FakeResponse(429, {"message": "quota"})

    result = ResendEmailClient(fetcher=fetcher).send(
        to_email="owner@example.com",
        subject="Hola",
        body="Mensaje",
    )

    assert result["sent"] is False
    assert result["status_code"] == 429
    assert "Resend HTTP 429" in result["error"]


def test_resend_error_transient_only_for_5xx():
    assert ResendEmailError("server", status_code=500).is_transient is True
    assert ResendEmailError("quota", status_code=429).is_transient is False
    assert ResendEmailError("auth", status_code=401).is_transient is False
    assert ResendEmailError("bad", status_code=400).is_transient is False
