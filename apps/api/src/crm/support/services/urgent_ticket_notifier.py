"""SupportUrgentTicketNotifier: notify the owner once per urgent/critical ticket.

No notifications app exists yet, so this is an explicit adapter: it persists a
``support.owner_notified.v1`` outbox event, records an ``owner_notified`` ticket
event, audits, and (best-effort) queues a WhatsApp message to the owner number
when configured. Idempotent: guarded by a ticket-event existence check + a
metadata flag, so the same ticket is never notified twice.
"""

import logging

from django.conf import settings
from django.db import transaction

from crm.audit.services import audit_event_create
from crm.core.services.outbox import create_outbox_event
from crm.support.domain import events
from crm.support.domain.enums import ActorType, TicketEventType
from crm.support.models import SupportTicket, SupportTicketEvent

from ._support import org_stub, record_event

logger = logging.getLogger(__name__)


class SupportUrgentTicketNotifier:
    @staticmethod
    @transaction.atomic
    def notify(*, ticket: SupportTicket, reason: str = "", actor=None, request=None) -> bool:
        """Returns True if a notification was emitted, False if already notified."""
        locked = SupportTicket.objects.select_for_update().get(id=ticket.id)
        already = (
            locked.metadata.get("owner_notified")
            or SupportTicketEvent.objects.filter(
                ticket=locked, event_type=TicketEventType.OWNER_NOTIFIED
            ).exists()
        )
        if already:
            return False

        locked.metadata = {**(locked.metadata or {}), "owner_notified": True}
        locked.save(update_fields=["metadata", "updated_at"])

        record_event(
            locked,
            event_type=TicketEventType.OWNER_NOTIFIED,
            actor_type=ActorType.SYSTEM.value if actor is None else ActorType.USER.value,
            actor_id=getattr(actor, "id", None),
            payload={"reason": reason[:300], "priority": locked.priority},
        )
        create_outbox_event(
            event_type=events.OWNER_NOTIFIED,
            organization_id=locked.organization_id,
            payload={
                "event_type": events.OWNER_NOTIFIED,
                "organization_id": str(locked.organization_id),
                "data": {
                    "ticket_id": str(locked.id),
                    "priority": locked.priority,
                    "title": locked.title[:200],
                    "reason": reason[:300],
                },
                "metadata": {"request_id": getattr(request, "request_id", None)},
            },
        )
        audit_event_create(
            event_type="support_owner_notified",
            actor=actor,
            organization=org_stub(locked.organization_id),
            request=request,
            resource_type="support_ticket",
            resource_id=str(locked.id),
            metadata={"priority": locked.priority, "reason": reason[:200]},
        )
        SupportUrgentTicketNotifier._best_effort_whatsapp(locked, reason)
        return True

    @staticmethod
    def _best_effort_whatsapp(ticket: SupportTicket, reason: str) -> None:
        """Queue an owner WhatsApp message via the conversations/whatsapp layer.

        Never raises into the caller: notification persistence already happened.
        """
        owner_number = getattr(settings, "OWNER_WHATSAPP_NUMBER", "")
        if not owner_number:
            return
        try:
            from crm.support.services.owner_whatsapp_adapter import notify_owner_via_whatsapp

            notify_owner_via_whatsapp(ticket=ticket, owner_number=owner_number, reason=reason)
        except Exception:  # pragma: no cover - best effort only
            logger.warning(
                "Owner WhatsApp notification skipped",
                extra={
                    "event": "support.owner_whatsapp_skipped",
                    "metadata": {"ticket_id": str(ticket.id)},
                },
            )
