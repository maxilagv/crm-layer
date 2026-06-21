"""Resend client for prospecting email sends.

Network access is behind an injectable fetcher. Any provider or parsing error
returns a non-sent result instead of raising into outreach flows.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings

_URL = "https://api.resend.com/emails"
_TIMEOUT = 12.0


@dataclass(frozen=True)
class ResendEmailResult:
    sent: bool
    message_id: str = ""
    error: str = ""
    status_code: int | None = None

    def as_dict(self) -> dict:
        return {
            "sent": self.sent,
            "message_id": self.message_id,
            "error": self.error,
            "status_code": self.status_code,
        }


class ResendEmailClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        from_email: str | None = None,
        fetcher=None,
        timeout: float = _TIMEOUT,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "RESEND_API_KEY", "")
        self.from_email = (
            from_email if from_email is not None else getattr(settings, "DEFAULT_FROM_EMAIL", "")
        )
        self._fetch = fetcher or self._default_fetch
        self.timeout = timeout

    def _default_fetch(self, url: str, payload: dict, headers: dict, timeout: float) -> dict:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        return _json_or_raise(response)

    def send(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        headers: dict | None = None,
    ) -> dict:
        to_email = (to_email or "").strip()
        subject = (subject or "").strip()
        body = (body or "").strip()
        if not self.api_key or not self.from_email or not to_email or not subject or not body:
            return ResendEmailResult(sent=False, error="missing_required_input").as_dict()

        payload = {
            "from": self.from_email,
            "to": [to_email],
            "subject": subject,
            "text": body,
        }
        if headers:
            payload["headers"] = headers
        request_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            data = _coerce_payload(self._fetch(_URL, payload, request_headers, self.timeout))
        except ResendEmailError as exc:
            return ResendEmailResult(
                sent=False,
                error=str(exc),
                status_code=exc.status_code,
            ).as_dict()
        except Exception as exc:  # noqa: BLE001 - email delivery must fail closed
            return ResendEmailResult(sent=False, error=type(exc).__name__).as_dict()

        message_id = str(data.get("id") or data.get("message_id") or "").strip()
        return ResendEmailResult(sent=bool(message_id), message_id=message_id).as_dict()


class ResendEmailError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

    @property
    def is_transient(self) -> bool:
        return self.status_code is not None and self.status_code >= 500


def _coerce_payload(payload) -> dict:
    if hasattr(payload, "status_code"):
        return _json_or_raise(payload)
    return payload if isinstance(payload, dict) else {}


def _json_or_raise(response) -> dict:
    try:
        data = response.json()
    except ValueError:
        data = {}
    if response.status_code >= 400:
        message = ""
        if isinstance(data, dict):
            message = str(data.get("message") or data.get("error") or "")
        raise ResendEmailError(
            f"Resend HTTP {response.status_code}: {message}",
            status_code=response.status_code,
        )
    return data or {}
