from dataclasses import dataclass

import requests
from django.conf import settings

from crm.whatsapp.clients.meta_client import MetaAPIError
from crm.whatsapp.domain import policies


@dataclass(frozen=True)
class RetrievedMedia:
    url: str
    mime_type: str = ""
    sha256: str = ""
    file_size: int | None = None


@dataclass(frozen=True)
class DownloadedMedia:
    content: bytes
    mime_type: str = ""
    size_bytes: int = 0


class MediaClient:
    def __init__(
        self,
        *,
        access_token: str | None = None,
        base_url: str | None = None,
        graph_api_version: str | None = None,
        timeout: float | None = None,
        download_timeout: float | None = None,
        session=None,
    ):
        self.access_token = (
            access_token if access_token is not None else settings.WHATSAPP_ACCESS_TOKEN
        )
        self.base_url = (base_url or policies.api_base_url()).rstrip("/")
        self.graph_api_version = graph_api_version or policies.graph_api_version()
        self.timeout = timeout if timeout is not None else policies.request_timeout_seconds()
        self.download_timeout = (
            download_timeout
            if download_timeout is not None
            else policies.media_download_timeout_seconds()
        )
        self.session = session or requests.Session()

    def retrieve_media_url(self, media_id: str) -> RetrievedMedia:
        if not self.access_token:
            raise MetaAPIError("WhatsApp access token is not configured", code="missing_token")
        url = f"{self.base_url}/{self.graph_api_version}/{media_id}"
        try:
            response = self.session.get(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise MetaAPIError(
                "Media URL request timed out",
                code="timeout",
                retryable=True,
            ) from exc
        except requests.RequestException as exc:
            raise MetaAPIError(
                "Media URL request failed", code="request_failed", retryable=True
            ) from exc
        data = response.json() if response.content else {}
        if response.status_code >= 400:
            error = data.get("error", {}) if isinstance(data, dict) else {}
            raise MetaAPIError(
                str(error.get("message") or "Meta media retrieval failed")[:500],
                code=str(error.get("code") or response.status_code),
                retryable=response.status_code >= 500,
                response_payload=data,
            )
        return RetrievedMedia(
            url=data.get("url", ""),
            mime_type=data.get("mime_type", ""),
            sha256=data.get("sha256", ""),
            file_size=data.get("file_size"),
        )

    def download_media(self, media_url: str) -> DownloadedMedia:
        if not self.access_token:
            raise MetaAPIError("WhatsApp access token is not configured", code="missing_token")
        try:
            response = self.session.get(
                media_url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=self.download_timeout,
                stream=False,
            )
        except requests.Timeout as exc:
            raise MetaAPIError("Media download timed out", code="timeout", retryable=True) from exc
        except requests.RequestException as exc:
            raise MetaAPIError(
                "Media download failed",
                code="request_failed",
                retryable=True,
            ) from exc
        if response.status_code >= 400:
            raise MetaAPIError(
                "Meta media download failed",
                code=str(response.status_code),
                retryable=response.status_code >= 500,
            )
        content = response.content or b""
        if len(content) > policies.MAX_MEDIA_SIZE_BYTES:
            raise MetaAPIError("Media exceeds maximum supported size", code="media_too_large")
        return DownloadedMedia(
            content=content,
            mime_type=response.headers.get("Content-Type", ""),
            size_bytes=len(content),
        )
