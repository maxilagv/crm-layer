"""WhatsApp media download into a private MediaAsset.

Runs in a worker (never in the webhook request). Uses the whatsapp module's
MediaClient through a thin adapter — Meta is never called from here. Idempotent
by WhatsApp media reference: a second download returns the existing asset.
"""

import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from crm.audit.services import audit_event_create
from crm.media.domain.enums import (
    MediaSource,
    ProcessingJobStatus,
    ProcessingJobType,
)
from crm.media.domain.exceptions import RetryableMediaError
from crm.media.models import MediaAsset, MediaProcessingJob

from ._support import org_stub
from .media_asset_creator import MediaAssetCreator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchedMedia:
    content: bytes
    mime_type: str
    sha256: str
    file_name: str


class WhatsAppMediaClientAdapter:
    """Bridges to the whatsapp MediaClient; the only Meta-facing dependency."""

    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            from crm.whatsapp.clients.media_client import MediaClient

            self._client = MediaClient()
        return self._client

    def fetch(self, external_media_id: str, *, fallback_name: str = "audio") -> FetchedMedia:
        from crm.whatsapp.clients.meta_client import MetaAPIError

        try:
            retrieved = self.client.retrieve_media_url(external_media_id)
            downloaded = self.client.download_media(retrieved.url)
        except MetaAPIError as exc:
            raise RetryableMediaError(str(exc)) from exc
        mime = downloaded.mime_type or retrieved.mime_type or "application/octet-stream"
        extension = mime.split("/")[-1] if "/" in mime else "bin"
        return FetchedMedia(
            content=downloaded.content,
            mime_type=mime,
            sha256=retrieved.sha256 or "",
            file_name=f"{fallback_name}.{extension}",
        )


class MediaDownloader:
    @staticmethod
    def download_from_whatsapp_reference(
        *, media_reference_id, adapter: WhatsAppMediaClientAdapter | None = None, actor=None
    ) -> MediaAsset:
        from crm.whatsapp.models import WhatsAppMediaReference

        reference = WhatsAppMediaReference.objects.get(id=media_reference_id)
        organization_id = reference.organization_id

        # Idempotency: a MediaAsset already linked to this reference is reused.
        existing_id = (reference.metadata or {}).get("media_asset_id")
        if existing_id:
            existing = MediaAsset.objects.filter(
                id=existing_id, organization_id=organization_id
            ).first()
            if existing is not None:
                return existing

        with transaction.atomic():
            job = MediaProcessingJob.objects.create(
                organization_id=organization_id,
                job_type=ProcessingJobType.DOWNLOAD,
                status=ProcessingJobStatus.RUNNING,
                started_at=timezone.now(),
                metadata={"whatsapp_media_reference_id": str(reference.id)},
            )

        adapter = adapter or WhatsAppMediaClientAdapter()
        try:
            fetched = adapter.fetch(
                reference.external_media_id, fallback_name=reference.file_name or "media"
            )
            asset = MediaAssetCreator.create_from_bytes(
                organization_id=organization_id,
                content=fetched.content,
                file_name=fetched.file_name,
                mime_type=fetched.mime_type,
                source=MediaSource.WHATSAPP,
                owner_type="whatsapp_media_reference",
                owner_id=reference.id,
                actor=actor,
                extra_metadata={"external_media_id": reference.external_media_id},
            )
        except Exception as exc:
            with transaction.atomic():
                job.status = ProcessingJobStatus.FAILED
                job.error_message = str(exc)[:500]
                job.attempts = job.attempts + 1
                job.finished_at = timezone.now()
                job.save(
                    update_fields=[
                        "status",
                        "error_message",
                        "attempts",
                        "finished_at",
                        "updated_at",
                    ]
                )
            logger.warning(
                "WhatsApp media download failed",
                extra={
                    "event": "media.download_failed",
                    "metadata": {"media_reference_id": str(reference.id)},
                },
            )
            raise RetryableMediaError(str(exc)) from exc

        with transaction.atomic():
            reference.metadata = {
                **(reference.metadata or {}),
                "media_asset_id": str(asset.id),
                "media_asset_integration": "linked",
            }
            reference.save(update_fields=["metadata", "updated_at"])
            job.media_asset = asset
            job.status = ProcessingJobStatus.SUCCESS
            job.finished_at = timezone.now()
            job.save(update_fields=["media_asset", "status", "finished_at", "updated_at"])
            # Link the CRM MessageAttachment to this asset when present.
            if reference.crm_attachment_id:
                attachment = reference.crm_attachment
                if hasattr(attachment, "media_asset_id"):
                    attachment.media_asset_id = asset.id
                    attachment.save(update_fields=["media_asset_id", "updated_at"])

        audit_event_create(
            event_type="media_asset_downloaded",
            actor=actor,
            organization=org_stub(organization_id),
            resource_type="media_media_asset",
            resource_id=str(asset.id),
            metadata={"external_media_id": reference.external_media_id},
        )
        return asset
