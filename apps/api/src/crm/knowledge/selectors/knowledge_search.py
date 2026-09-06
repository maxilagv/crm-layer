"""Semantic retrieval for business knowledge chunks."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from pgvector.django import CosineDistance

from crm.ai.models import AIEmbedding
from crm.ai.services.ai_gateway import AIGateway
from crm.knowledge.models import KnowledgeChunk
from crm.knowledge.services.knowledge_ingestion import KNOWLEDGE_EMBEDDING_OWNER_TYPE

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KnowledgeSearchResult:
    chunk: KnowledgeChunk
    score: float


class KnowledgeRetriever:
    @staticmethod
    def search(
        *,
        organization_id,
        query_text: str,
        k: int = 4,
        threshold: float | None = None,
        metadata: dict | None = None,
    ) -> list[KnowledgeSearchResult]:
        try:
            if not _knowledge_exists(organization_id):
                return []
            qvec = _query_vector(organization_id, query_text, metadata=metadata)
            if not qvec:
                return []
            rows = list(
                AIEmbedding.objects.filter(
                    organization_id=organization_id,
                    owner_type=KNOWLEDGE_EMBEDDING_OWNER_TYPE,
                    vector__isnull=False,
                )
                .annotate(distance=CosineDistance("vector", qvec))
                .order_by("distance")[: max(1, k)]
            )
            chunks_by_id = {
                chunk.id: chunk
                for chunk in KnowledgeChunk.objects.filter(
                    organization_id=organization_id,
                    id__in=[row.owner_id for row in rows],
                    document__deleted_at__isnull=True,
                    document__source__deleted_at__isnull=True,
                ).select_related("document", "document__source")
            }
            results: list[KnowledgeSearchResult] = []
            for row in rows:
                chunk = chunks_by_id.get(row.owner_id)
                if chunk is None:
                    continue
                score = 1.0 - float(row.distance)
                if threshold is not None and score < threshold:
                    continue
                results.append(KnowledgeSearchResult(chunk=chunk, score=score))
            return results[: max(1, k)]
        except Exception as exc:
            logger.warning(
                "Knowledge retrieval failed",
                extra={
                    "event": "knowledge.retrieve_failed",
                    "organization_id": str(organization_id),
                    "metadata": {"error": str(exc)},
                },
            )
            return []


def _knowledge_exists(organization_id) -> bool:
    return bool(
        cache.get_or_set(
            f"kb-exists:{organization_id}",
            lambda: KnowledgeChunk.objects.filter(
                organization_id=organization_id,
                document__deleted_at__isnull=True,
                document__source__deleted_at__isnull=True,
            ).exists(),
            timeout=settings.KNOWLEDGE_CACHE_TTL,
        )
    )


def _query_vector(organization_id, query_text: str, *, metadata: dict | None = None):
    query_hash = hashlib.sha256((query_text or "").encode()).hexdigest()
    cache_key = f"kb-qvec:{organization_id}:{query_hash}"
    if not metadata:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    result = AIGateway.create_embedding_vector(
        organization_id=organization_id,
        text=query_text or "",
        metadata=metadata,
    )
    if not result.succeeded or not result.data:
        return []
    vector = result.data.get("vector") or []
    if not metadata:
        cache.set(cache_key, vector, timeout=settings.KNOWLEDGE_CACHE_TTL)
    return vector
