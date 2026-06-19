from django.db import IntegrityError, transaction

from crm.core.services.outbox import create_outbox_event
from crm.sales.domain import events
from crm.sales.domain.enums import ObjectionType
from crm.sales.domain.rules import detect_objection_type
from crm.sales.models import SalesObjection


@transaction.atomic
def detect_and_record_objection(*, lead, message=None, conversation=None, text: str = ""):
    objection_type = detect_objection_type(text)
    if objection_type is None:
        return None
    try:
        objection, created = SalesObjection.objects.get_or_create(
            organization_id=lead.organization_id,
            lead=lead,
            objection_type=objection_type,
            message=message,
            defaults={
                "contact": lead.contact,
                "conversation": conversation,
                "summary": _summary_for(objection_type),
                "raw_text": text[:4000],
            },
        )
    except IntegrityError:
        return SalesObjection.objects.filter(
            organization_id=lead.organization_id,
            lead=lead,
            objection_type=objection_type,
            message=message,
        ).first()
    if created:
        create_outbox_event(
            event_type=events.SALES_OBJECTION_DETECTED,
            organization_id=lead.organization_id,
            payload={
                "lead_id": str(lead.id),
                "objection_id": str(objection.id),
                "objection_type": objection_type,
            },
        )
    return objection


def _summary_for(objection_type: str) -> str:
    if objection_type == ObjectionType.PRICE.value:
        return "Objecion de precio detectada."
    if objection_type == ObjectionType.TIME.value:
        return "Objecion de tiempo detectada."
    if objection_type == ObjectionType.NOT_INTERESTED.value:
        return "Lead indico que no tiene interes."
    return "Objecion comercial detectada."


class SalesObjectionHandler:
    @staticmethod
    def handle(*, lead, message=None, conversation=None, text: str = ""):
        return detect_and_record_objection(
            lead=lead, message=message, conversation=conversation, text=text
        )
