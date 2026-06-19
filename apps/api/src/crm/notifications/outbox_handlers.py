"""Outbox handlers for notifications.

Connects the owner-WhatsApp notification event (emitted by WhatsAppOwnerNotifier)
to the actual unofficial-bridge outbound queue, so reminders/alerts reach the
owner's phone instead of staying as in-app notifications only.
"""

import logging

from django.conf import settings

from crm.core.services.outbox import register_outbox_handler
from crm.notifications.services.whatsapp_owner_notifier import OWNER_WHATSAPP_OUTBOX_EVENT

logger = logging.getLogger(__name__)


def _owner_phone(organization, payload_phone: str) -> str:
    """Resolve the owner's WhatsApp number: payload → BusinessProfile → env."""
    if payload_phone:
        return payload_phone
    from crm.business_settings.models import BusinessProfile

    profile = BusinessProfile.objects.filter(organization_id=organization.id).first()
    return (getattr(profile, "owner_phone", "") or "") or (
        getattr(settings, "OWNER_WHATSAPP_NUMBER", "") or ""
    )


@register_outbox_handler(OWNER_WHATSAPP_OUTBOX_EVENT)
def handle_owner_whatsapp_message(event) -> None:
    """Queue an owner notification for delivery through the WhatsApp bridge."""
    data = (event.payload or {}).get("data", {})
    body = (data.get("body") or "").strip()
    if not body:
        return

    from crm.contacts.constants import ContactSource, ContactType
    from crm.contacts.services import ContactResolver
    from crm.organizations.models import Organization
    from crm.whatsapp.services.outbound_queue import WhatsAppOutboundQueueService

    organization = Organization.objects.filter(id=event.organization_id).first()
    if organization is None:
        return

    phone = _owner_phone(organization, data.get("owner_phone") or "")
    if not phone:
        logger.warning(
            "Owner WhatsApp notification skipped: no owner phone configured",
            extra={"event": "notifications.owner_whatsapp_no_phone"},
        )
        return

    # The owner is an INTERNAL contact, never a lead/prospect.
    resolved = ContactResolver.resolve_by_phone(
        organization=organization,
        raw_phone=phone,
        create=True,
        contact_type=ContactType.INTERNAL,
        source=ContactSource.SYSTEM,
    )
    WhatsAppOutboundQueueService.enqueue(
        organization=organization,
        phone=phone,
        body=body,
        contact=resolved.contact,
        idempotency_key=f"owner-notif:{data.get('delivery_id') or event.id}",
    )


# Event emitted by the AI `notify_owner` tool (crm.ai.domain.events.EVENT_AI_OWNER_NOTIFICATION).
_AI_OWNER_NOTIFICATION_EVENT = "ai.owner_notification_requested.v1"


@register_outbox_handler(_AI_OWNER_NOTIFICATION_EVENT)
def handle_ai_owner_notification(event) -> None:
    """Deliver an owner alert raised by the agent (in-app + WhatsApp via the router)."""
    data = (event.payload or {}).get("data", {})
    reason = (data.get("reason") or "").strip()
    if not reason:
        return

    from crm.notifications.domain.enums import NotificationPriority, NotificationType
    from crm.notifications.services.notification_service import NotificationService
    from crm.organizations.models import Organization

    organization = Organization.objects.filter(id=event.organization_id).first()
    if organization is None:
        return

    urgency = str(data.get("urgency") or "medium").lower()
    priority = (
        NotificationPriority.URGENT.value if urgency == "high" else NotificationPriority.HIGH.value
    )
    NotificationService.notify_owner(
        organization=organization,
        notification_type=NotificationType.SYSTEM_ALERT.value,
        title="El agente pide tu atención",
        body=reason,
        priority=priority,
        deduplication_key=f"ai-owner-notif:{data.get('ai_run_id') or event.id}",
    )
