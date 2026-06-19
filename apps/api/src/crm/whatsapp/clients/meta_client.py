from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings

from crm.core.logging import sanitize
from crm.whatsapp.domain import policies


class MetaAPIError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "",
        retryable: bool = False,
        response_payload: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.response_payload = sanitize(response_payload or {})


@dataclass(frozen=True)
class MetaMessageResponse:
    external_message_id: str
    raw_response: dict[str, Any]


class MetaClient:
    """Small WhatsApp Cloud API client isolated behind gateway DTOs."""

    def __init__(
        self,
        *,
        access_token: str | None = None,
        base_url: str | None = None,
        graph_api_version: str | None = None,
        timeout: float | None = None,
        session=None,
    ):
        self.access_token = (
            access_token if access_token is not None else settings.WHATSAPP_ACCESS_TOKEN
        )
        self.base_url = (base_url or policies.api_base_url()).rstrip("/")
        self.graph_api_version = graph_api_version or policies.graph_api_version()
        self.timeout = timeout if timeout is not None else policies.request_timeout_seconds()
        self.session = session or requests.Session()

    def send_text_message(
        self,
        *,
        phone_number_id: str,
        recipient_phone: str,
        body: str,
        context: dict[str, Any] | None = None,
    ) -> MetaMessageResponse:
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        if context:
            payload["context"] = context
        return self._send_message(phone_number_id=phone_number_id, payload=payload)

    def send_template_message(
        self,
        *,
        phone_number_id: str,
        recipient_phone: str,
        template_name: str,
        language: str,
        components: list[dict[str, Any]] | None = None,
    ) -> MetaMessageResponse:
        template: dict[str, Any] = {
            "name": template_name,
            "language": {"code": language},
        }
        if components:
            template["components"] = components
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "template",
            "template": template,
        }
        return self._send_message(phone_number_id=phone_number_id, payload=payload)

    def _send_message(
        self,
        *,
        phone_number_id: str,
        payload: dict[str, Any],
    ) -> MetaMessageResponse:
        data = self._request("post", f"/{phone_number_id}/messages", json=payload)
        messages = data.get("messages") or []
        external_message_id = messages[0].get("id", "") if messages else ""
        if not external_message_id:
            raise MetaAPIError("Meta response did not include a message id", response_payload=data)
        return MetaMessageResponse(
            external_message_id=external_message_id,
            raw_response=sanitize(data),
        )

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        if not self.access_token:
            raise MetaAPIError("WhatsApp access token is not configured", code="missing_token")
        url = f"{self.base_url}/{self.graph_api_version}{path}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.Timeout as exc:
            raise MetaAPIError("Meta request timed out", code="timeout", retryable=True) from exc
        except requests.RequestException as exc:
            raise MetaAPIError(
                "Meta request failed",
                code="request_failed",
                retryable=True,
            ) from exc

        try:
            data = response.json() if response.content else {}
        except ValueError:
            data = {"non_json_response": True}

        if response.status_code >= 400:
            error = data.get("error") if isinstance(data, dict) else {}
            code = str(error.get("code") or response.status_code)
            message = str(error.get("message") or "Meta API error")
            retryable = response.status_code >= 500
            raise MetaAPIError(
                message[:500],
                code=code,
                retryable=retryable,
                response_payload=sanitize(data),
            )
        return data
