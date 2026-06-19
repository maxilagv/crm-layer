from django.db import IntegrityError, transaction
from django.utils import timezone

from crm.core.services.outbox import create_outbox_event
from crm.leads.domain.enums import LeadStage, StageChangedByType
from crm.leads.services.lead_lifecycle import change_stage
from crm.sales.domain import events
from crm.sales.models import OPEN_CALL_REQUEST_STATUSES, SalesCallRequest


@transaction.atomic
def create_call_request(*, lead, conversation=None, notes: str = "", actor=None):
    existing = SalesCallRequest.objects.filter(
        organization_id=lead.organization_id,
        lead=lead,
        status__in=OPEN_CALL_REQUEST_STATUSES,
    ).first()
    if existing:
        return existing, False
    try:
        call_request = SalesCallRequest.objects.create(
            organization_id=lead.organization_id,
            lead=lead,
            contact=lead.contact,
            conversation=conversation,
            notes=notes[:4000],
            requested_at=timezone.now(),
            created_by_id=getattr(actor, "id", None),
        )
    except IntegrityError:
        return (
            SalesCallRequest.objects.filter(
                organization_id=lead.organization_id,
                lead=lead,
                status__in=OPEN_CALL_REQUEST_STATUSES,
            ).first(),
            False,
        )
    if lead.stage != LeadStage.CALL_REQUESTED.value:
        change_stage(
            lead=lead,
            to_stage=LeadStage.CALL_REQUESTED.value,
            reason="call_requested",
            changed_by_type=StageChangedByType.AI_AGENT.value
            if actor is None
            else StageChangedByType.USER.value,
            actor=actor,
        )
    create_outbox_event(
        event_type=events.SALES_CALL_REQUESTED,
        organization_id=lead.organization_id,
        payload={"lead_id": str(lead.id), "call_request_id": str(call_request.id)},
    )
    return call_request, True


def mark_call_request_scheduled(*, call_request: SalesCallRequest, scheduled_at, notes: str = ""):
    with transaction.atomic():
        call_request = SalesCallRequest.objects.select_for_update().get(id=call_request.id)
        call_request.mark_scheduled(scheduled_at, notes=notes)
        change_stage(
            lead=call_request.lead,
            to_stage=LeadStage.CALL_SCHEDULED.value,
            reason="call_scheduled",
            changed_by_type=StageChangedByType.USER.value,
        )
        create_outbox_event(
            event_type=events.SALES_CALL_SCHEDULED,
            organization_id=call_request.organization_id,
            payload={"call_request_id": str(call_request.id), "lead_id": str(call_request.lead_id)},
        )
    return call_request


class SalesCallCloser:
    @staticmethod
    def create_call_request(*, lead, conversation=None, notes: str = "", actor=None):
        return create_call_request(lead=lead, conversation=conversation, notes=notes, actor=actor)
