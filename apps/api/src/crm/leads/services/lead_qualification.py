from crm.leads.domain.enums import LeadStage
from crm.leads.models import Lead
from crm.sales.domain.enums import ObjectionType
from crm.sales.domain.rules import detect_objection_type

from .lead_lifecycle import change_stage, mark_unqualified


def detect_unqualified_from_text(*, lead: Lead, text: str, actor=None) -> Lead | None:
    objection = detect_objection_type(text)
    if objection == ObjectionType.NOT_INTERESTED.value:
        return mark_unqualified(lead=lead, reason="not_interested", actor=actor)
    lowered = (text or "").lower()
    if "spam" in lowered or "equivocado" in lowered:
        return mark_unqualified(lead=lead, reason="spam_or_wrong_contact", actor=actor)
    return None


def mark_nurturing(*, lead: Lead, reason: str = "nurturing", actor=None) -> Lead:
    return change_stage(lead=lead, to_stage=LeadStage.NURTURING.value, reason=reason, actor=actor)
