"""Celery workers for the AI platform.

Queues are assigned via CELERY_TASK_ROUTES in settings: hot paths (replies,
scoring) run on ``ai_fast``; summaries on ``ai_slow``; audio on
``transcription``; images on ``image_generation``; embeddings and evals on
their own queues. A slow image render never blocks a hot sales reply.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

_RETRY_KWARGS = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 300,
    "max_retries": 3,
    "retry_jitter": True,
}


@shared_task(name="ai.generate_sales_reply", **_RETRY_KWARGS)
def generate_sales_reply(*, conversation_id: str, message_id: str, lead_id: str | None = None):
    from crm.ai.services.ai_gateway import AIGateway

    result = AIGateway.generate_sales_reply(
        conversation_id=conversation_id, message_id=message_id, lead_id=lead_id
    )
    return str(result.run_id)


@shared_task(name="ai.generate_support_reply", **_RETRY_KWARGS)
def generate_support_reply(*, conversation_id: str, message_id: str, ticket_id: str | None = None):
    from crm.ai.services.ai_gateway import AIGateway

    result = AIGateway.generate_support_reply(
        conversation_id=conversation_id, message_id=message_id, ticket_id=ticket_id
    )
    return str(result.run_id)


@shared_task(name="ai.score_lead", **_RETRY_KWARGS)
def score_lead(*, conversation_id: str, lead_id: str | None = None):
    from crm.ai.services.ai_gateway import AIGateway

    result = AIGateway.score_lead(conversation_id=conversation_id, lead_id=lead_id)
    return str(result.run_id)


@shared_task(name="ai.extract_tasks", **_RETRY_KWARGS)
def extract_tasks(*, conversation_id: str, message_id: str):
    from crm.ai.services.ai_gateway import AIGateway

    result = AIGateway.extract_tasks(conversation_id=conversation_id, message_id=message_id)
    return str(result.run_id)


@shared_task(name="ai.summarize_conversation", **_RETRY_KWARGS)
def summarize_conversation(*, conversation_id: str, summary_type: str = "short"):
    from crm.ai.services.ai_gateway import AIGateway

    result = AIGateway.summarize_conversation(
        conversation_id=conversation_id, summary_type=summary_type
    )
    return str(result.run_id)


@shared_task(name="ai.extract_conversation_memory", **_RETRY_KWARGS)
def extract_conversation_memory(*, conversation_id: str):
    """Extract durable memory facts from a conversation and persist them (Phase 9.1)."""
    from crm.ai.services.ai_gateway import AIGateway
    from crm.conversations.models import Conversation
    from crm.conversations.services import ConversationMemoryService

    result = AIGateway.extract_memory(conversation_id=conversation_id)
    if result.succeeded and result.data:
        conversation = Conversation.objects.select_related("contact").get(id=conversation_id)
        ConversationMemoryService.persist_extracted_facts(
            conversation=conversation, facts=result.data.get("facts", [])
        )
    return str(result.run_id)


@shared_task(name="ai.transcribe_audio", **_RETRY_KWARGS)
def transcribe_audio(*, media_reference_id: str):
    from crm.ai.services.transcription_service import TranscriptionService

    result = TranscriptionService.transcribe_media_reference(media_reference_id=media_reference_id)
    return str(result.run_id)


@shared_task(name="ai.extract_ticket_from_audio", **_RETRY_KWARGS)
def extract_ticket_from_audio(
    *, organization_id: str, transcription: str, contact_id: str | None = None
):
    from crm.ai.services.ai_gateway import AIGateway
    from crm.contacts.models import Contact

    contact = Contact.objects.filter(id=contact_id).first() if contact_id else None
    result = AIGateway.extract_ticket_from_audio(
        organization_id=organization_id, transcription=transcription, contact=contact
    )
    return str(result.run_id)


@shared_task(name="ai.generate_image", **_RETRY_KWARGS)
def generate_image(*, organization_id: str, prompt: str, requested_by_run_id: str | None = None):
    from crm.ai.services.ai_gateway import AIGateway

    result = AIGateway.generate_image(
        organization_id=organization_id,
        image_request=prompt,
        metadata={"requested_by_run_id": requested_by_run_id},
    )
    return str(result.run_id)


@shared_task(name="ai.create_embeddings", **_RETRY_KWARGS)
def create_embeddings(
    *,
    organization_id: str,
    owner_type: str,
    owner_id: str,
    text: str,
    metadata: dict | None = None,
):
    from crm.ai.services.ai_gateway import AIGateway

    result = AIGateway.create_embedding(
        organization_id=organization_id,
        owner_type=owner_type,
        owner_id=owner_id,
        text=text,
        metadata=metadata,
    )
    if owner_type == "knowledge_chunk" and result.succeeded:
        from crm.knowledge.services.knowledge_ingestion import KnowledgeIngestionService

        KnowledgeIngestionService.mark_document_embedded_if_complete(chunk_id=owner_id)
    return str(result.run_id)


@shared_task(name="ai.run_eval_suite", ignore_result=False)
def run_eval_suite(*, organization_id: str, suite_name: str | None = None):
    from crm.ai.services.eval_runner import EvalRunner

    if suite_name:
        return EvalRunner.run_suite(organization_id=organization_id, suite_name=suite_name)
    return EvalRunner.run_all(organization_id=organization_id)


@shared_task(name="ai.cleanup_old_runs", ignore_result=True)
def cleanup_old_runs(*, days: int = 90):
    """Soft-delete AIRuns older than the retention window."""
    from crm.ai.models import AIRun

    threshold = timezone.now() - timedelta(days=days)
    updated = AIRun.objects.filter(created_at__lt=threshold).update(deleted_at=timezone.now())
    logger.info(
        "Old AI runs cleaned",
        extra={"event": "ai.cleanup_old_runs", "metadata": {"soft_deleted": updated}},
    )
    return updated


@shared_task(name="ai.recalculate_usage", ignore_result=True)
def recalculate_usage(*, organization_id: str | None = None):
    """Re-estimate costs after a pricing-table update."""
    from crm.ai.domain.value_objects import AIUsage
    from crm.ai.models import AIUsageRecord
    from crm.ai.services.cost_tracker import CostTracker

    queryset = AIUsageRecord.objects.all()
    if organization_id:
        queryset = queryset.filter(organization_id=organization_id)
    updated = 0
    for record in queryset.iterator():
        usage = AIUsage(
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            cached_tokens=record.cached_tokens,
            audio_seconds=record.audio_seconds,
            image_count=record.image_count,
        )
        new_cost = CostTracker.estimate_cost(model=record.model, usage=usage)
        if new_cost != record.estimated_cost:
            record.estimated_cost = new_cost
            record.save(update_fields=["estimated_cost", "updated_at"])
            record.ai_run.estimated_cost = new_cost
            record.ai_run.save(update_fields=["estimated_cost", "updated_at"])
            updated += 1
    return updated
