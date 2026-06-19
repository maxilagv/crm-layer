from celery import shared_task

from crm.organizations.models import Organization
from crm.whatsapp.clients.meta_client import MetaAPIError
from crm.whatsapp.services.inbound_message_handler import handle_inbound_messages
from crm.whatsapp.services.media_downloader import (
    RetryableMediaDownloadError,
    download_media_reference,
)
from crm.whatsapp.services.message_status_handler import handle_message_statuses
from crm.whatsapp.services.outbound_message_sender import (
    RetryableOutboundSendError,
    send_queued_outbound_message,
)
from crm.whatsapp.services.template_sync import (
    audit_template_sync_failed,
    sync_templates_for_organization,
)
from crm.whatsapp.services.webhook_processor import process_event


def _retry_countdown(retries: int) -> int:
    return min(30 * (retries + 1), 300)


@shared_task(
    name="whatsapp.process_webhook_event",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def process_webhook_event(self, webhook_event_id: str) -> None:
    try:
        process_event(webhook_event_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries)) from exc


@shared_task(
    name="whatsapp.handle_inbound_message",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def handle_inbound_message(self, webhook_event_id: str) -> int:
    from crm.whatsapp.models import WhatsAppWebhookEvent

    try:
        return handle_inbound_messages(WhatsAppWebhookEvent.objects.get(id=webhook_event_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries)) from exc


@shared_task(
    name="whatsapp.download_media",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def download_media(self, media_reference_id: str) -> None:
    try:
        download_media_reference(media_reference_id)
    except RetryableMediaDownloadError as exc:
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries)) from exc


@shared_task(
    name="whatsapp.send_outbound_message",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def send_outbound_message(self, outbound_message_id: str) -> None:
    try:
        send_queued_outbound_message(outbound_message_id)
    except RetryableOutboundSendError as exc:
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries)) from exc


@shared_task(
    name="whatsapp.update_message_status",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def update_message_status(self, webhook_event_id: str) -> int:
    from crm.whatsapp.models import WhatsAppWebhookEvent

    try:
        return handle_message_statuses(WhatsAppWebhookEvent.objects.get(id=webhook_event_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries)) from exc


@shared_task(
    name="whatsapp.sync_templates",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def sync_templates(self, organization_id: str) -> int:
    organization = Organization.objects.get(id=organization_id)
    try:
        return sync_templates_for_organization(organization=organization)
    except Exception as exc:
        audit_template_sync_failed(organization=organization, error=exc)
        if isinstance(exc, MetaAPIError) and exc.retryable:
            raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries)) from exc
        raise
