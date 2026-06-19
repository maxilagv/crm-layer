from typing import Any

import requests
from django.conf import settings

from crm.core.logging import sanitize
from crm.whatsapp.clients.meta_client import MetaAPIError
from crm.whatsapp.domain import policies


class TemplateClient:
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

    def list_templates(self, *, waba_id: str) -> list[dict[str, Any]]:
        if not self.access_token:
            raise MetaAPIError("WhatsApp access token is not configured", code="missing_token")
        url = f"{self.base_url}/{self.graph_api_version}/{waba_id}/message_templates"
        try:
            response = self.session.get(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise MetaAPIError("Template sync timed out", code="timeout", retryable=True) from exc
        except requests.RequestException as exc:
            raise MetaAPIError(
                "Template sync failed",
                code="request_failed",
                retryable=True,
            ) from exc
        data = response.json() if response.content else {}
        if response.status_code >= 400:
            error = data.get("error", {}) if isinstance(data, dict) else {}
            raise MetaAPIError(
                str(error.get("message") or "Template sync failed")[:500],
                code=str(error.get("code") or response.status_code),
                retryable=response.status_code >= 500,
                response_payload=sanitize(data),
            )
        return list(data.get("data") or [])
