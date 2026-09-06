"""EmbeddingService: create + dedupe embeddings through the gateway flow."""

import hashlib

from django.conf import settings

from crm.ai.domain.enums import AIPurpose, AIRunStatus, ModelCapability
from crm.ai.domain.exceptions import AIProviderError
from crm.ai.domain.result import AIGatewayResult
from crm.ai.domain.value_objects import AIRequest
from crm.ai.models import AIEmbedding

from .ai_run_logger import AIRunLogger
from .fallback_service import call_with_fallback
from .model_router import ModelRouter
from .usage_recorder import UsageRecorder


class EmbeddingService:
    @staticmethod
    def create(
        *, organization_id, owner_type: str, owner_id, text: str, metadata: dict | None = None
    ) -> AIGatewayResult:
        text_hash = hashlib.sha256((text or "").encode()).hexdigest()
        route = ModelRouter.route(
            organization_id=organization_id,
            purpose=AIPurpose.EMBEDDING.value,
            required_capabilities=(ModelCapability.EMBEDDINGS.value,),
        )

        existing = AIEmbedding.objects.filter(
            organization_id=organization_id,
            owner_type=owner_type,
            owner_id=owner_id,
            embedding_model=route.model_name,
            text_hash=text_hash,
        ).first()
        force_reindex = bool((metadata or {}).get("force_reindex"))
        if existing is not None and existing.vector is not None and not force_reindex:
            return AIGatewayResult(
                run_id=None,
                status=AIRunStatus.SUCCESS.value,
                purpose=AIPurpose.EMBEDDING.value,
                data={"embedding_id": str(existing.id), "deduplicated": True},
            )

        run = AIRunLogger.start(
            organization_id=organization_id,
            purpose=AIPurpose.EMBEDDING.value,
            input_messages=[],
            input_context={"owner_type": owner_type, "owner_id": str(owner_id)},
        )
        request = AIRequest(
            organization_id=organization_id,
            purpose=AIPurpose.EMBEDDING.value,
            embedding_input=text,
            metadata=dict(metadata or {}),
            request_id=str(run.id),
        )
        try:
            response, fallback_used = call_with_fallback(
                route=route, request=request, method_name="create_embedding"
            )
        except AIProviderError as exc:
            AIRunLogger.finish(
                run, status=AIRunStatus.FAILED, error_code=exc.code, error_message=str(exc)
            )
            return AIGatewayResult(
                run_id=run.id,
                status=run.status,
                purpose=AIPurpose.EMBEDDING.value,
                error_code=exc.code,
                error_message=str(exc),
            )

        AIRunLogger.record_response(run, response)
        dimension_error = _embedding_dimension_error(response.embedding_vector)
        if dimension_error:
            AIRunLogger.finish(
                run,
                status=AIRunStatus.FAILED,
                error_code="embedding_dim_mismatch",
                error_message=dimension_error,
            )
            return AIGatewayResult(
                run_id=run.id,
                status=run.status,
                purpose=AIPurpose.EMBEDDING.value,
                error_code="embedding_dim_mismatch",
                error_message=dimension_error,
                provider=response.provider,
                model=response.model,
                latency_ms=response.latency_ms,
            )

        if existing is not None:
            existing.vector = response.embedding_vector
            existing.source_text = text[:4000]
            existing.embedding_model = response.model
            existing.save(update_fields=["vector", "source_text", "embedding_model", "updated_at"])
            embedding = existing
        else:
            embedding = AIEmbedding.objects.create(
                organization_id=organization_id,
                owner_type=owner_type,
                owner_id=owner_id,
                embedding_model=response.model,
                vector=response.embedding_vector,
                text_hash=text_hash,
                source_text=text[:4000],
            )
        UsageRecorder.record(run=run, usage=response.usage)
        AIRunLogger.finish(
            run,
            status=AIRunStatus.FALLBACK_USED if fallback_used else AIRunStatus.SUCCESS,
        )
        return AIGatewayResult(
            run_id=run.id,
            status=run.status,
            purpose=AIPurpose.EMBEDDING.value,
            data={"embedding_id": str(embedding.id), "dimensions": len(response.embedding_vector)},
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
        )

    @staticmethod
    def create_vector(
        *, organization_id, text: str, metadata: dict | None = None
    ) -> AIGatewayResult:
        """Create an embedding vector without persisting an AIEmbedding row."""
        route = ModelRouter.route(
            organization_id=organization_id,
            purpose=AIPurpose.EMBEDDING.value,
            required_capabilities=(ModelCapability.EMBEDDINGS.value,),
        )
        run = AIRunLogger.start(
            organization_id=organization_id,
            purpose=AIPurpose.EMBEDDING.value,
            input_messages=[],
            input_context={"mode": "query_vector"},
        )
        request = AIRequest(
            organization_id=organization_id,
            purpose=AIPurpose.EMBEDDING.value,
            embedding_input=text,
            metadata=dict(metadata or {}),
            request_id=str(run.id),
        )
        try:
            response, fallback_used = call_with_fallback(
                route=route, request=request, method_name="create_embedding"
            )
        except AIProviderError as exc:
            AIRunLogger.finish(
                run, status=AIRunStatus.FAILED, error_code=exc.code, error_message=str(exc)
            )
            return AIGatewayResult(
                run_id=run.id,
                status=run.status,
                purpose=AIPurpose.EMBEDDING.value,
                error_code=exc.code,
                error_message=str(exc),
            )

        AIRunLogger.record_response(run, response)
        dimension_error = _embedding_dimension_error(response.embedding_vector)
        if dimension_error:
            AIRunLogger.finish(
                run,
                status=AIRunStatus.FAILED,
                error_code="embedding_dim_mismatch",
                error_message=dimension_error,
            )
            return AIGatewayResult(
                run_id=run.id,
                status=run.status,
                purpose=AIPurpose.EMBEDDING.value,
                error_code="embedding_dim_mismatch",
                error_message=dimension_error,
                provider=response.provider,
                model=response.model,
                latency_ms=response.latency_ms,
            )
        UsageRecorder.record(run=run, usage=response.usage)
        AIRunLogger.finish(
            run,
            status=AIRunStatus.FALLBACK_USED if fallback_used else AIRunStatus.SUCCESS,
        )
        return AIGatewayResult(
            run_id=run.id,
            status=run.status,
            purpose=AIPurpose.EMBEDDING.value,
            data={
                "vector": response.embedding_vector,
                "dimensions": len(response.embedding_vector),
            },
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
        )


def _embedding_dimension_error(vector: list[float]) -> str:
    expected = settings.AI_EMBEDDING_DIMENSIONS
    actual = len(vector or [])
    if actual == expected:
        return ""
    return f"Embedding dimension mismatch: expected {expected}, got {actual}"
