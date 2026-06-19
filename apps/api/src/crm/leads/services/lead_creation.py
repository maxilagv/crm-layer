from django.db import IntegrityError, transaction

from crm.audit.services import audit_event_create
from crm.contacts.constants import ContactType
from crm.core.services.outbox import create_outbox_event
from crm.leads.domain import events
from crm.leads.domain.enums import LeadSourceType, LeadStage, LeadStatus, StageChangedByType
from crm.leads.domain.rules import can_auto_create_lead
from crm.leads.domain.value_objects import LeadCreationResult
from crm.leads.models import Lead, LeadSource

from .lead_lifecycle import record_stage_history


def _source_type_for_conversation(conversation) -> str:
    if conversation is None:
        return LeadSourceType.MANUAL.value
    if conversation.channel == "whatsapp":
        return LeadSourceType.WHATSAPP.value
    return LeadSourceType.UNKNOWN.value


@transaction.atomic
def create_or_get_lead_from_conversation(
    *,
    organization,
    conversation,
    message=None,
    explicit: bool = False,
    actor=None,
    request=None,
    metadata: dict | None = None,
) -> LeadCreationResult:
    contact = conversation.contact
    allowed, reason = can_auto_create_lead(contact, conversation, explicit=explicit)
    if not allowed:
        return LeadCreationResult(lead=None, created=False, reason=reason)

    existing = Lead.objects.filter(
        organization_id=organization.id,
        contact=contact,
        status=LeadStatus.ACTIVE.value,
    ).first()
    if existing is not None:
        return LeadCreationResult(lead=existing, created=False, reason="existing_active_lead")

    try:
        lead = Lead.objects.create(
            organization_id=organization.id,
            contact=contact,
            stage=LeadStage.NEW.value,
            status=LeadStatus.ACTIVE.value,
            metadata=metadata or {},
            created_by_id=getattr(actor, "id", None),
        )
    except IntegrityError:
        lead = Lead.objects.get(
            organization_id=organization.id,
            contact=contact,
            status=LeadStatus.ACTIVE.value,
        )
        return LeadCreationResult(lead=lead, created=False, reason="existing_active_lead")

    if contact.type == ContactType.UNKNOWN:
        contact.type = ContactType.LEAD
        contact.save(update_fields=["type", "updated_at"])

    LeadSource.objects.create(
        organization_id=organization.id,
        lead=lead,
        source_type=_source_type_for_conversation(conversation),
        source_detail="conversation",
        channel=getattr(conversation, "channel", "") or "",
        first_touch_message=message,
        first_touch_conversation=conversation,
        metadata={"created_from": "conversation"},
    )
    record_stage_history(
        lead=lead,
        from_stage="",
        to_stage=LeadStage.NEW.value,
        reason="lead_created",
        changed_by_type=StageChangedByType.SYSTEM.value,
        actor=actor,
    )
    create_outbox_event(
        event_type=events.LEAD_CREATED,
        organization_id=organization.id,
        payload={
            "lead_id": str(lead.id),
            "contact_id": str(contact.id),
            "conversation_id": str(conversation.id),
        },
    )
    audit_event_create(
        event_type="lead_created",
        actor=actor,
        organization=organization,
        request=request,
        resource_type="lead",
        resource_id=str(lead.id),
        metadata={"source": _source_type_for_conversation(conversation)},
    )
    return LeadCreationResult(lead=lead, created=True, reason="created")


@transaction.atomic
def create_manual_lead(
    *,
    organization,
    contact,
    actor=None,
    request=None,
    source_type: str = LeadSourceType.MANUAL.value,
    metadata: dict | None = None,
) -> LeadCreationResult:
    existing = Lead.objects.filter(
        organization_id=organization.id,
        contact=contact,
        status=LeadStatus.ACTIVE.value,
    ).first()
    if existing:
        return LeadCreationResult(lead=existing, created=False, reason="existing_active_lead")
    allowed, reason = can_auto_create_lead(contact, None, explicit=True)
    if not allowed:
        return LeadCreationResult(lead=None, created=False, reason=reason)
    lead = Lead.objects.create(
        organization_id=organization.id,
        contact=contact,
        status=LeadStatus.ACTIVE.value,
        stage=LeadStage.NEW.value,
        metadata=metadata or {},
        created_by_id=getattr(actor, "id", None),
    )
    if contact.type == ContactType.UNKNOWN:
        contact.type = ContactType.LEAD
        contact.save(update_fields=["type", "updated_at"])
    LeadSource.objects.create(
        organization_id=organization.id,
        lead=lead,
        source_type=source_type,
        source_detail="manual",
    )
    record_stage_history(
        lead=lead,
        from_stage="",
        to_stage=LeadStage.NEW.value,
        reason="manual_lead_created",
        changed_by_type=StageChangedByType.USER.value if actor else StageChangedByType.SYSTEM.value,
        actor=actor,
    )
    audit_event_create(
        event_type="lead_created",
        actor=actor,
        organization=organization,
        request=request,
        resource_type="lead",
        resource_id=str(lead.id),
        metadata={"source": source_type},
    )
    return LeadCreationResult(lead=lead, created=True, reason="created")
