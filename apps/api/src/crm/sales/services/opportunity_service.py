from django.db import transaction

from crm.core.services.outbox import create_outbox_event
from crm.sales.domain import events
from crm.sales.domain.enums import OpportunityStage
from crm.sales.models import SalesOpportunity


def probability_for_score(score: int) -> int:
    if score >= 90:
        return 90
    if score >= 76:
        return 75
    if score >= 56:
        return 50
    if score >= 31:
        return 25
    return 10


@transaction.atomic
def create_or_update_opportunity_for_lead(*, lead, actor=None) -> SalesOpportunity:
    opportunity = (
        SalesOpportunity.objects.select_for_update()
        .filter(organization_id=lead.organization_id, lead=lead)
        .order_by("-created_at")
        .first()
    )
    created = False
    if opportunity is None:
        opportunity = SalesOpportunity.objects.create(
            organization_id=lead.organization_id,
            lead=lead,
            contact=lead.contact,
            title=f"Oportunidad - {lead.contact.display_name}",
            probability=probability_for_score(lead.score),
            stage=OpportunityStage.WON.value
            if lead.status == "won"
            else OpportunityStage.NEW.value,
            created_by_id=getattr(actor, "id", None),
        )
        created = True
    else:
        opportunity.probability = probability_for_score(lead.score)
        if lead.status == "won":
            opportunity.stage = OpportunityStage.WON.value
            opportunity.probability = 100
        opportunity.save(update_fields=["probability", "stage", "updated_at"])
    if created:
        create_outbox_event(
            event_type=events.SALES_OPPORTUNITY_CREATED,
            organization_id=lead.organization_id,
            payload={"lead_id": str(lead.id), "opportunity_id": str(opportunity.id)},
        )
    return opportunity


@transaction.atomic
def create_opportunity(
    *,
    lead,
    title: str = "",
    value_estimate_min=None,
    value_estimate_max=None,
    currency: str = "USD",
    stage: str = OpportunityStage.NEW.value,
    probability: int | None = None,
    expected_close_date=None,
    actor=None,
    metadata: dict | None = None,
) -> SalesOpportunity:
    opportunity = SalesOpportunity.objects.create(
        organization_id=lead.organization_id,
        lead=lead,
        contact=lead.contact,
        title=(title or f"Oportunidad - {lead.contact.display_name}")[:255],
        value_estimate_min=value_estimate_min,
        value_estimate_max=value_estimate_max,
        currency=currency or "USD",
        stage=stage,
        probability=probability if probability is not None else probability_for_score(lead.score),
        expected_close_date=expected_close_date,
        metadata=metadata or {},
        created_by_id=getattr(actor, "id", None),
    )
    create_outbox_event(
        event_type=events.SALES_OPPORTUNITY_CREATED,
        organization_id=lead.organization_id,
        payload={"lead_id": str(lead.id), "opportunity_id": str(opportunity.id)},
    )
    return opportunity


class OpportunityService:
    @staticmethod
    def create_or_update_for_lead(*, lead, actor=None):
        return create_or_update_opportunity_for_lead(lead=lead, actor=actor)

    @staticmethod
    def create(*, lead, **kwargs):
        return create_opportunity(lead=lead, **kwargs)
