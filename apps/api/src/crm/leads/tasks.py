from celery import shared_task

from crm.conversations.models import Conversation
from crm.leads.services.lead_creation import create_or_get_lead_from_conversation
from crm.leads.services.lead_scoring import score_lead
from crm.organizations.models import Organization
from crm.sales.services.sales_conversation_agent import notify_owner_for_hot_lead


def _retry_countdown(retries: int) -> int:
    return min(30 * (retries + 1), 300)


@shared_task(
    name="leads.score_lead_from_conversation",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def score_lead_from_conversation(self, conversation_id: str) -> str | None:
    try:
        conversation = Conversation.objects.select_related("contact").get(id=conversation_id)
        organization = Organization.objects.get(id=conversation.organization_id)
        message = conversation.messages.order_by("-created_at").first()
        result = create_or_get_lead_from_conversation(
            organization=organization,
            conversation=conversation,
            message=message,
        )
        if result.lead is None:
            return None
        scored = score_lead(lead=result.lead, conversation=conversation)
        return str(scored.snapshot.id) if scored.snapshot else None
    except Exception as exc:
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries)) from exc


@shared_task(
    name="leads.detect_hot_lead",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def detect_hot_lead(self, lead_id: str) -> bool:
    try:
        from crm.leads.models import Lead

        lead = Lead.objects.get(id=lead_id)
        if lead.score >= 76:
            return notify_owner_for_hot_lead(lead=lead, reason="hot_lead_worker")
        return False
    except Exception as exc:
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries)) from exc
