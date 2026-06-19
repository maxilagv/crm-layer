"""Support Celery workers (idempotent, retry-safe).

Tickets dedupe by source_message_id; owner notifications dedupe per ticket;
support replies go through SafetyGuard. Queues (settings): ai_fast for triage /
reply; transcription for create_ticket_from_audio.
"""

from celery import shared_task

_RETRY = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 300,
    "max_retries": 3,
    "retry_jitter": True,
}


@shared_task(name="support.create_ticket_from_audio", **_RETRY)
def create_ticket_from_audio(
    *,
    media_asset_id: str,
    contact_id: str,
    conversation_id: str | None = None,
    source_message_id: str | None = None,
):
    from crm.contacts.models import Contact
    from crm.media.models import MediaAsset
    from crm.support.services.ticket_from_audio import AudioTicketExtractor

    media_asset = MediaAsset.objects.get(id=media_asset_id)
    contact = Contact.objects.get(id=contact_id)
    result = AudioTicketExtractor.run(
        media_asset=media_asset,
        contact=contact,
        conversation_id=conversation_id,
        source_message_id=source_message_id,
    )
    return result.ticket_id


@shared_task(name="support.triage_ticket", **_RETRY)
def triage_ticket(*, ticket_id: str):
    from crm.support.domain.enums import ActorType, TicketEventType
    from crm.support.models import SupportTicket
    from crm.support.services._support import record_event
    from crm.support.services.ticket_triage import SupportTriageService

    ticket = SupportTicket.objects.get(id=ticket_id)
    triage = SupportTriageService.triage(
        text=f"{ticket.title}\n{ticket.description}", organization_id=ticket.organization_id
    )
    changed = ticket.priority != triage.priority or ticket.category != triage.category
    if changed:
        ticket.priority = triage.priority
        ticket.category = triage.category
        ticket.save(update_fields=["priority", "category", "updated_at"])
        record_event(
            ticket,
            event_type=TicketEventType.PRIORITY_CHANGED,
            actor_type=ActorType.WORKER.value,
            payload=triage.as_dict(),
        )
    return ticket_id


@shared_task(name="support.generate_support_reply", **_RETRY)
def generate_support_reply(*, conversation_id: str, message_id: str, ticket_id: str | None = None):
    from crm.support.services.support_reply import SupportReplyService

    result = SupportReplyService.generate(
        conversation_id=conversation_id, message_id=message_id, ticket_id=ticket_id
    )
    return result.run_id


@shared_task(name="support.notify_owner_for_urgent_ticket", **_RETRY)
def notify_owner_for_urgent_ticket(*, ticket_id: str, reason: str = ""):
    from crm.support.models import SupportTicket
    from crm.support.services.urgent_ticket_notifier import SupportUrgentTicketNotifier

    ticket = SupportTicket.objects.get(id=ticket_id)
    notified = SupportUrgentTicketNotifier.notify(ticket=ticket, reason=reason)
    return notified
