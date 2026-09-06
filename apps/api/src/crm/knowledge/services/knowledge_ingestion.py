"""Knowledge ingestion: idempotent documents, overlapping chunks and embeddings."""

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction

from crm.ai.models import AIEmbedding
from crm.ai.tasks import create_embeddings
from crm.knowledge.models import KnowledgeChunk, KnowledgeDocument, KnowledgeSource, sha256_text
from crm.media.services.media_storage import MediaStorageService

logger = logging.getLogger(__name__)

KNOWLEDGE_EMBEDDING_OWNER_TYPE = "knowledge_chunk"


class KnowledgeIngestionService:
    @staticmethod
    @transaction.atomic
    def ingest_text(
        *,
        organization_id,
        source: KnowledgeSource,
        title: str,
        raw_text: str,
    ) -> KnowledgeDocument:
        content_hash = sha256_text(raw_text)
        document, created = KnowledgeDocument.objects.get_or_create(
            organization_id=organization_id,
            source=source,
            content_hash=content_hash,
            defaults={
                "title": title or source.name,
                "raw_text": raw_text or "",
                "ingest_status": KnowledgeDocument.IngestStatus.PENDING,
            },
        )
        if not created:
            KnowledgeIngestionService.mark_document_embedded_if_complete(document=document)
            return document

        source.status = KnowledgeSource.Status.ACTIVE
        source.save(update_fields=["status", "updated_at"])
        KnowledgeIngestionService._chunk_and_enqueue(document)
        cache.delete(_kb_exists_cache_key(organization_id))
        return document

    @staticmethod
    @transaction.atomic
    def ingest_existing_document(document: KnowledgeDocument) -> KnowledgeDocument:
        if document.source.source_type == KnowledgeSource.SourceType.PDF:
            return KnowledgeIngestionService.ingest_pdf_document(document)
        if document.raw_text:
            return KnowledgeIngestionService._process_document_text(document, document.raw_text)
        document.ingest_status = KnowledgeDocument.IngestStatus.FAILED
        document.error_message = "Document has no text to ingest"
        document.save(update_fields=["ingest_status", "error_message", "updated_at"])
        return document

    @staticmethod
    @transaction.atomic
    def ingest_pdf_document(document: KnowledgeDocument) -> KnowledgeDocument:
        media_asset_id = (document.metadata or {}).get("media_asset_id")
        try:
            if not media_asset_id:
                raise RuntimeError("PDF document has no media_asset_id")
            from crm.media.models import MediaAsset

            media_asset = MediaAsset.objects.get(
                organization_id=document.organization_id,
                id=media_asset_id,
            )
            content = MediaStorageService.open_asset(media_asset)
            from .pdf_extractor import extract_pdf_text

            raw_text = extract_pdf_text(content)
        except Exception as exc:
            logger.warning(
                "Knowledge PDF ingestion failed",
                extra={
                    "event": "knowledge.pdf_ingest_failed",
                    "organization_id": str(document.organization_id),
                    "metadata": {"document_id": str(document.id), "error": str(exc)},
                },
            )
            document.ingest_status = KnowledgeDocument.IngestStatus.FAILED
            document.error_message = str(exc)[:4000]
            document.source.status = KnowledgeSource.Status.FAILED
            document.source.save(update_fields=["status", "updated_at"])
            document.save(update_fields=["ingest_status", "error_message", "updated_at"])
            return document

        return KnowledgeIngestionService._process_document_text(document, raw_text)

    @staticmethod
    def ingest_pdf(
        *,
        organization_id,
        source: KnowledgeSource,
        title: str,
        pdf_bytes: bytes | None = None,
        media_asset=None,
    ) -> KnowledgeDocument:
        if media_asset is not None:
            content = MediaStorageService.open_asset(media_asset)
        else:
            content = pdf_bytes or b""
        content_hash = sha256_text(content.decode("latin1", errors="ignore"))
        document, _ = KnowledgeDocument.objects.get_or_create(
            organization_id=organization_id,
            source=source,
            content_hash=content_hash,
            defaults={
                "title": title or source.name,
                "raw_text": "",
                "ingest_status": KnowledgeDocument.IngestStatus.PENDING,
                "metadata": {"media_asset_id": str(media_asset.id)} if media_asset else {},
            },
        )
        if media_asset is not None and not document.metadata.get("media_asset_id"):
            document.metadata = {**document.metadata, "media_asset_id": str(media_asset.id)}
            document.save(update_fields=["metadata", "updated_at"])
        return KnowledgeIngestionService.ingest_pdf_document(document)

    @staticmethod
    def mark_document_embedded_if_complete(
        *, chunk_id=None, document: KnowledgeDocument | None = None
    ) -> KnowledgeDocument | None:
        if document is None:
            chunk = KnowledgeChunk.objects.filter(id=chunk_id).select_related("document").first()
            if chunk is None:
                return None
            document = chunk.document

        chunks = list(
            KnowledgeChunk.objects.filter(
                organization_id=document.organization_id,
                document=document,
            ).values_list("id", flat=True)
        )
        if not chunks:
            return document
        embedded_count = AIEmbedding.objects.filter(
            organization_id=document.organization_id,
            owner_type=KNOWLEDGE_EMBEDDING_OWNER_TYPE,
            owner_id__in=chunks,
            vector__isnull=False,
        ).count()
        if embedded_count == len(chunks):
            if document.ingest_status != KnowledgeDocument.IngestStatus.EMBEDDED:
                document.ingest_status = KnowledgeDocument.IngestStatus.EMBEDDED
                document.error_message = ""
                document.save(update_fields=["ingest_status", "error_message", "updated_at"])
            return document
        if document.ingest_status == KnowledgeDocument.IngestStatus.PENDING:
            document.ingest_status = KnowledgeDocument.IngestStatus.CHUNKED
            document.save(update_fields=["ingest_status", "updated_at"])
        return document

    @staticmethod
    def _process_document_text(document: KnowledgeDocument, raw_text: str) -> KnowledgeDocument:
        content_hash = sha256_text(raw_text)
        document.raw_text = raw_text or ""
        document.content_hash = content_hash
        document.error_message = ""
        document.ingest_status = KnowledgeDocument.IngestStatus.PENDING
        try:
            document.save(
                update_fields=[
                    "raw_text",
                    "content_hash",
                    "error_message",
                    "ingest_status",
                    "updated_at",
                ]
            )
        except IntegrityError:
            existing = KnowledgeDocument.objects.filter(
                organization_id=document.organization_id,
                source=document.source,
                content_hash=content_hash,
            ).first()
            if existing is not None:
                return existing
            raise
        KnowledgeIngestionService._chunk_and_enqueue(document)
        cache.delete(_kb_exists_cache_key(document.organization_id))
        return document

    @staticmethod
    def _chunk_and_enqueue(document: KnowledgeDocument) -> None:
        KnowledgeChunk.all_objects.filter(
            organization_id=document.organization_id,
            document=document,
        ).delete()
        chunks = _chunk_text(
            document.raw_text,
            chunk_size=settings.KNOWLEDGE_CHUNK_SIZE,
            overlap=settings.KNOWLEDGE_CHUNK_OVERLAP,
        )
        chunk_objects = [
            KnowledgeChunk(
                organization_id=document.organization_id,
                document=document,
                chunk_index=index,
                content=chunk,
                content_hash=sha256_text(chunk),
                token_estimate=max(1, len(chunk) // 4),
            )
            for index, chunk in enumerate(chunks)
        ]
        KnowledgeChunk.objects.bulk_create(chunk_objects)
        document.ingest_status = KnowledgeDocument.IngestStatus.CHUNKED
        document.save(update_fields=["ingest_status", "updated_at"])
        for chunk in KnowledgeChunk.objects.filter(
            organization_id=document.organization_id,
            document=document,
        ).order_by("chunk_index"):
            transaction.on_commit(
                lambda chunk_id=str(chunk.id), content=chunk.content: create_embeddings.delay(
                    organization_id=str(document.organization_id),
                    owner_type=KNOWLEDGE_EMBEDDING_OWNER_TYPE,
                    owner_id=chunk_id,
                    text=content,
                    metadata=None,
                )
            )
        KnowledgeIngestionService.mark_document_embedded_if_complete(document=document)


def _chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    chunk_size = max(1, chunk_size)
    overlap = max(0, min(overlap, chunk_size - 1))
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _kb_exists_cache_key(organization_id) -> str:
    return f"kb-exists:{organization_id}"
