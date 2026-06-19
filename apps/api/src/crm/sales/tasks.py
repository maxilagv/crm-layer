from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from crm.conversations.models import Conversation, Message
from crm.leads.models import Lead
from crm.organizations.models import Organization
from crm.sales.services.followup_service import create_followup
from crm.sales.services.sales_conversation_agent import (
    SalesConversationAgent,
    notify_owner_for_hot_lead,
)
from crm.sales.services.sales_objection_handler import detect_and_record_objection


def _retry_countdown(retries: int) -> int:
    return min(30 * (retries + 1), 300)


@shared_task(
    name="sales.generate_sales_reply",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def generate_sales_reply(self, conversation_id: str, message_id: str) -> str:
    try:
        conversation = Conversation.objects.select_related("contact").get(id=conversation_id)
        message = Message.objects.get(id=message_id, conversation=conversation)
        organization = Organization.objects.get(id=conversation.organization_id)
        result = SalesConversationAgent.generate_reply(
            conversation=conversation,
            message=message,
            organization=organization,
        )
        return str(result.ai_run_id or "")
    except Exception as exc:
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries)) from exc


@shared_task(
    name="sales.handle_objection",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def handle_objection(self, lead_id: str, message_id: str) -> str | None:
    try:
        lead = Lead.objects.select_related("contact").get(id=lead_id)
        message = Message.objects.select_related("conversation").get(id=message_id)
        objection = detect_and_record_objection(
            lead=lead,
            message=message,
            conversation=message.conversation,
            text=message.body,
        )
        return str(objection.id) if objection else None
    except Exception as exc:
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries)) from exc


@shared_task(
    name="sales.create_followup_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def create_followup_task(self, lead_id: str, title: str = "Seguimiento comercial") -> str:
    try:
        lead = Lead.objects.select_related("contact").get(id=lead_id)
        followup, _created = create_followup(
            lead=lead,
            due_at=timezone.now() + timedelta(days=2),
            title=title,
            idempotency_key=f"worker:{lead.id}:{title}",
        )
        return str(followup.id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries)) from exc


@shared_task(
    name="sales.notify_owner_for_hot_lead",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    ignore_result=True,
)
def notify_owner_task(self, lead_id: str) -> bool:
    try:
        lead = Lead.objects.get(id=lead_id)
        return notify_owner_for_hot_lead(lead=lead, reason="sales_worker")
    except Exception as exc:
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries)) from exc
