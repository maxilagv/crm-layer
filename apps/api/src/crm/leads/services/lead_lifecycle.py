from django.db import transaction
from django.utils import timezone

from crm.audit.services import audit_event_create
from crm.core.services.outbox import create_outbox_event
from crm.leads.domain import events
from crm.leads.domain.enums import LeadStage, LeadStatus, StageChangedByType
from crm.leads.models import Lead, LeadStageHistory

TERMINAL_STAGE_STATUS = {
    LeadStage.WON.value: LeadStatus.WON.value,
    LeadStage.LOST.value: LeadStatus.LOST.value,
    LeadStage.UNQUALIFIED.value: LeadStatus.UNQUALIFIED.value,
    LeadStage.NURTURING.value: LeadStatus.NURTURING.value,
}


def _actor_id(actor) -> object | None:
    return getattr(actor, "id", None) if actor is not None else None


def record_stage_history(
    *,
    lead: Lead,
    from_stage: str,
    to_stage: str,
    reason: str = "",
    changed_by_type: str = StageChangedByType.SYSTEM.value,
    actor=None,
    ai_run_id=None,
    metadata: dict | None = None,
) -> LeadStageHistory | None:
    if from_stage == to_stage:
        return None
    history = LeadStageHistory.objects.create(
        organization_id=lead.organization_id,
        lead=lead,
        from_stage=from_stage,
        to_stage=to_stage,
        reason=reason[:1000],
        changed_by_id=_actor_id(actor),
        changed_by_type=changed_by_type,
        ai_run_id=ai_run_id,
        metadata=metadata or {},
    )
    create_outbox_event(
        event_type=events.LEAD_STAGE_CHANGED,
        organization_id=lead.organization_id,
        payload={
            "lead_id": str(lead.id),
            "from_stage": from_stage,
            "to_stage": to_stage,
            "reason": reason[:500],
        },
    )
    return history


@transaction.atomic
def change_stage(
    *,
    lead: Lead,
    to_stage: str,
    reason: str = "",
    changed_by_type: str = StageChangedByType.SYSTEM.value,
    actor=None,
    ai_run_id=None,
    request=None,
    metadata: dict | None = None,
) -> Lead:
    lead = Lead.objects.select_for_update().get(id=lead.id)
    from_stage = lead.stage
    if from_stage == to_stage:
        return lead
    lead.stage = to_stage
    if to_stage in TERMINAL_STAGE_STATUS:
        lead.status = TERMINAL_STAGE_STATUS[to_stage]
    lead.updated_by_id = _actor_id(actor)
    lead.save(update_fields=["stage", "status", "updated_by_id", "updated_at"])
    record_stage_history(
        lead=lead,
        from_stage=from_stage,
        to_stage=to_stage,
        reason=reason,
        changed_by_type=changed_by_type,
        actor=actor,
        ai_run_id=ai_run_id,
        metadata=metadata,
    )
    audit_event_create(
        event_type="lead_stage_changed",
        actor=actor,
        organization=_org_stub(lead.organization_id),
        request=request,
        resource_type="lead",
        resource_id=str(lead.id),
        changes={"stage": {"from": from_stage, "to": to_stage}},
        metadata={"reason": reason[:500], "changed_by_type": changed_by_type},
    )
    return lead


def mark_lost(*, lead: Lead, reason: str, actor=None, request=None) -> Lead:
    with transaction.atomic():
        lead = change_stage(
            lead=lead,
            to_stage=LeadStage.LOST.value,
            reason=reason,
            changed_by_type=StageChangedByType.USER.value
            if actor
            else StageChangedByType.SYSTEM.value,
            actor=actor,
            request=request,
            metadata={"lost_reason": reason[:1000]},
        )
        lead.metadata = {
            **(lead.metadata or {}),
            "lost_reason": reason[:1000],
            "lost_at": timezone.now().isoformat(),
        }
        lead.save(update_fields=["metadata", "updated_at"])
        create_outbox_event(
            event_type=events.LEAD_LOST,
            organization_id=lead.organization_id,
            payload={"lead_id": str(lead.id), "reason": reason[:500]},
        )
    return lead


def mark_unqualified(*, lead: Lead, reason: str, actor=None, request=None) -> Lead:
    lead = change_stage(
        lead=lead,
        to_stage=LeadStage.UNQUALIFIED.value,
        reason=reason,
        changed_by_type=StageChangedByType.USER.value if actor else StageChangedByType.SYSTEM.value,
        actor=actor,
        request=request,
        metadata={"unqualified_reason": reason[:1000]},
    )
    create_outbox_event(
        event_type=events.LEAD_UNQUALIFIED,
        organization_id=lead.organization_id,
        payload={"lead_id": str(lead.id), "reason": reason[:500]},
    )
    return lead


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()
