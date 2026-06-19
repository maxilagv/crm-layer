from django.db import IntegrityError, transaction

from crm.core.services.outbox import create_outbox_event
from crm.sales.domain import events
from crm.sales.models import SalesFollowup


@transaction.atomic
def create_followup(
    *,
    lead,
    due_at,
    title: str,
    notes: str = "",
    conversation=None,
    actor=None,
    idempotency_key: str = "",
):
    key = idempotency_key or f"lead:{lead.id}:followup:{due_at.date()}:{title[:80]}"
    existing = SalesFollowup.objects.filter(
        organization_id=lead.organization_id,
        idempotency_key=key,
    ).first()
    if existing:
        return existing, False
    try:
        followup = SalesFollowup.objects.create(
            organization_id=lead.organization_id,
            lead=lead,
            contact=lead.contact,
            conversation=conversation,
            title=title[:255],
            notes=notes[:4000],
            due_at=due_at,
            idempotency_key=key,
            created_by_id=getattr(actor, "id", None),
        )
    except IntegrityError:
        return SalesFollowup.objects.get(
            organization_id=lead.organization_id, idempotency_key=key
        ), False
    create_outbox_event(
        event_type=events.SALES_FOLLOWUP_CREATED,
        organization_id=lead.organization_id,
        payload={"lead_id": str(lead.id), "followup_id": str(followup.id)},
    )
    return followup, True


class FollowupService:
    @staticmethod
    def create(*, lead, due_at, title: str, notes: str = "", conversation=None, actor=None):
        return create_followup(
            lead=lead,
            due_at=due_at,
            title=title,
            notes=notes,
            conversation=conversation,
            actor=actor,
        )
