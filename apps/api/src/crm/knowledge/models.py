"""Business knowledge base models.

Knowledge chunks reuse ``crm.ai.AIEmbedding`` instead of a KnowledgeEmbedding
table. The embedding row is addressed with ``owner_type="knowledge_chunk"`` and
``owner_id=KnowledgeChunk.id`` so retrieval can share the generic AI embedding
pipeline, dedupe and pgvector index.
"""

import hashlib

from django.db import models

from crm.core.models import BaseModel


def sha256_text(value: str) -> str:
    return hashlib.sha256((value or "").encode()).hexdigest()


class KnowledgeSource(BaseModel):
    class SourceType(models.TextChoices):
        MANUAL_TEXT = "manual_text", "Manual text"
        PDF = "pdf", "PDF"
        FAQ = "faq", "FAQ"
        CONVERSATION = "conversation", "Conversation"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"
        FAILED = "failed", "Failed"

    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=32, choices=SourceType.choices)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = "knowledge_source"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "name", "source_type"],
                name="uniq_knowledge_source_org_name_type",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "source_type", "status"]),
        ]

    def __str__(self) -> str:
        return self.name


class KnowledgeDocument(BaseModel):
    class IngestStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        CHUNKED = "chunked", "Chunked"
        EMBEDDED = "embedded", "Embedded"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(KnowledgeSource, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    raw_text = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64)
    ingest_status = models.CharField(
        max_length=24, choices=IngestStatus.choices, default=IngestStatus.PENDING
    )
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "knowledge_document"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "source", "content_hash"],
                name="uniq_knowledge_doc_org_source_hash",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "source", "ingest_status"]),
            models.Index(fields=["content_hash"]),
        ]

    def __str__(self) -> str:
        return self.title


class KnowledgeChunk(BaseModel):
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    content_hash = models.CharField(max_length=64)
    token_estimate = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "knowledge_chunk"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "document", "chunk_index"],
                name="uniq_knowledge_chunk_org_doc_index",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "document"]),
            models.Index(fields=["content_hash"]),
        ]
        ordering = ["document_id", "chunk_index"]

    def __str__(self) -> str:
        return f"{self.document_id}:{self.chunk_index}"
