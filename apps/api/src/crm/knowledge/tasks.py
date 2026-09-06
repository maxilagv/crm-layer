from celery import shared_task

from crm.ai.tasks import _RETRY_KWARGS


@shared_task(name="knowledge.ingest_document", **_RETRY_KWARGS)
def ingest_document(*, document_id: str):
    from crm.knowledge.models import KnowledgeDocument
    from crm.knowledge.services.knowledge_ingestion import KnowledgeIngestionService

    document = KnowledgeDocument.objects.select_related("source").get(id=document_id)
    KnowledgeIngestionService.ingest_existing_document(document)
    return document_id
