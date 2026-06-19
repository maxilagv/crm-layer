from django.db import transaction

from crm.audit.services import audit_event_create
from crm.contacts.constants import ContactType
from crm.core.services.outbox import create_outbox_event
from crm.leads.domain import events
from crm.leads.domain.enums import LeadStage, StageChangedByType
from crm.leads.models import Lead

from .lead_lifecycle import change_stage


@transaction.atomic
def convert_to_client(*, lead: Lead, actor=None, request=None, reason: str = "") -> Lead:
    lead = Lead.objects.select_for_update().select_related("contact").get(id=lead.id)
    contact = lead.contact
    if contact.type != ContactType.CLIENT:
        contact.type = ContactType.CLIENT
        contact.save(update_fields=["type", "updated_at"])
    if lead.stage != LeadStage.WON.value:
        lead = change_stage(
            lead=lead,
            to_stage=LeadStage.WON.value,
            reason=reason or "converted_to_client",
            changed_by_type=StageChangedByType.USER.value
            if actor
            else StageChangedByType.SYSTEM.value,
            actor=actor,
            request=request,
        )
    from crm.sales.services.opportunity_service import create_or_update_opportunity_for_lead

    create_or_update_opportunity_for_lead(lead=lead, actor=actor)
    create_outbox_event(
        event_type=events.LEAD_CONVERTED_TO_CLIENT,
        organization_id=lead.organization_id,
        payload={"lead_id": str(lead.id), "contact_id": str(contact.id)},
    )
    audit_event_create(
        event_type="lead_converted_to_client",
        actor=actor,
        organization=_org_stub(lead.organization_id),
        request=request,
        resource_type="lead",
        resource_id=str(lead.id),
        metadata={"contact_id": str(contact.id)},
    )
    return lead


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()
