"""Shared helpers for support services: event recording, org stub."""

from crm.support.domain.enums import ActorType
from crm.support.models import SupportTicketEvent


def org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()


def record_event(
    ticket,
    *,
    event_type: str,
    actor_type: str = ActorType.SYSTEM.value,
    actor_id=None,
    from_status: str = "",
    to_status: str = "",
    payload: dict | None = None,
) -> SupportTicketEvent:
    return SupportTicketEvent.objects.create(
        organization_id=ticket.organization_id,
        ticket=ticket,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        from_status=from_status,
        to_status=to_status,
        payload=payload or {},
    )
