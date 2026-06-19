from django.db import transaction
from django.utils import timezone

from crm.audit.services import audit_event_create
from crm.core.services.outbox import create_outbox_event
from crm.whatsapp.clients.media_client import MediaClient
from crm.whatsapp.clients.meta_client import MetaAPIError
from crm.whatsapp.domain import events, policies
from crm.whatsapp.domain.enums import MediaReferenceStatus
from crm.whatsapp.models import WhatsAppMediaReference


class RetryableMediaDownloadError(Exception):
    """Media download failed after state was persisted and can be retried by Celery."""


def _mime_allowed(mime_type: str) -> bool:
    if not mime_type:
        return True
    return any(mime_type.startswith(prefix) for prefix in policies.ALLOWED_MEDIA_MIME_PREFIXES)


def download_media_reference(
    media_reference_id,
    *,
    client: MediaClient | None = None,
) -> WhatsAppMediaReference:
    with transaction.atomic():
        reference = WhatsAppMediaReference.objects.select_for_update().get(id=media_reference_id)
        if reference.status == MediaReferenceStatus.DOWNLOADED:
            return reference
        if reference.status not in {
            MediaReferenceStatus.RECEIVED,
            MediaReferenceStatus.QUEUED,
            MediaReferenceStatus.FAILED,
        }:
            return reference
        reference.status = MediaReferenceStatus.DOWNLOADING
        reference.save(update_fields=["status", "updated_at"])

    client = client or MediaClient()
    try:
        retrieved = client.retrieve_media_url(reference.external_media_id)
        downloaded = client.download_media(retrieved.url)
        mime_type = downloaded.mime_type or retrieved.mime_type or reference.mime_type
        if not _mime_allowed(mime_type):
            raise MetaAPIError("Unsupported media MIME type", code="unsupported_media_type")
        if downloaded.size_bytes < 0:
            raise MetaAPIError("Invalid media size", code="invalid_media_size")
    except MetaAPIError as exc:
        with transaction.atomic():
            reference = WhatsAppMediaReference.objects.select_for_update().get(
                id=media_reference_id
            )
            reference.status = MediaReferenceStatus.FAILED
            reference.failed_at = timezone.now()
            reference.error_message = str(exc)[:500]
            reference.save(update_fields=["status", "failed_at", "error_message", "updated_at"])
        audit_event_create(
            event_type="whatsapp_media_download_failed",
            organization=_org_stub(reference.organization_id),
            resource_type="whatsapp_media_reference",
            resource_id=str(reference.id),
            metadata={"external_media_id": reference.external_media_id},
        )
        if exc.retryable:
            raise RetryableMediaDownloadError(str(exc)) from exc
        return reference

    with transaction.atomic():
        reference = WhatsAppMediaReference.objects.select_for_update().get(id=media_reference_id)
        reference.status = MediaReferenceStatus.DOWNLOADED
        reference.downloaded_at = timezone.now()
        reference.mime_type = mime_type
        reference.sha256 = retrieved.sha256 or reference.sha256
        reference.size_bytes = downloaded.size_bytes
        reference.error_message = ""
        reference.metadata = {
            **(reference.metadata or {}),
            "downloaded_bytes": downloaded.size_bytes,
            "media_asset_integration": "pending",
        }
        reference.save(
            update_fields=[
                "status",
                "downloaded_at",
                "mime_type",
                "sha256",
                "size_bytes",
                "error_message",
                "metadata",
                "updated_at",
            ]
        )
        if reference.crm_attachment_id:
            attachment = reference.crm_attachment
            attachment.mime_type = reference.mime_type
            attachment.size_bytes = reference.size_bytes
            attachment.save(update_fields=["mime_type", "size_bytes", "updated_at"])
        create_outbox_event(
            event_type=events.MEDIA_DOWNLOADED,
            organization_id=reference.organization_id,
            payload={"media_reference_id": str(reference.id)},
        )
    return reference


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()
