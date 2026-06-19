"""Adapter to send the owner an urgent-ticket summary over WhatsApp.

Support never calls Meta directly: it goes through the whatsapp module's
outbound sender, exactly like any other outbound message. Best-effort: callers
treat failures as non-fatal (the notification is already persisted).
"""

from crm.support.models import SupportTicket


def notify_owner_via_whatsapp(*, ticket: SupportTicket, owner_number: str, reason: str) -> None:
    from crm.contacts.services import ContactResolver
    from crm.conversations.constants import Channel
    from crm.conversations.services import ConversationResolver
    from crm.organizations.models import Organization
    from crm.whatsapp.services.outbound_message_sender import queue_text_message

    organization = Organization.objects.get(id=ticket.organization_id)
    resolved = ContactResolver.resolve_by_phone(
        organization=organization, raw_phone=owner_number, create=True
    )
    if resolved.contact is None:
        return
    conversation = ConversationResolver.resolve(
        organization=organization, contact=resolved.contact, channel=Channel.WHATSAPP
    ).conversation
    body = (
        f"🚨 Ticket {ticket.priority.upper()}: {ticket.title}\n"
        f"{ticket.ai_summary or ticket.description[:300]}\n"
        f"Motivo: {reason[:200]}"
    )
    queue_text_message(
        organization=organization,
        conversation=conversation,
        contact=resolved.contact,
        body=body,
        idempotency_key=f"owner-notify-{ticket.id}",
    )
