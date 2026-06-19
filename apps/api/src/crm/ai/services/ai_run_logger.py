"""AIRunLogger: every provider call has a persisted AIRun, created BEFORE the call.

The logger also persists per-role AIMessages and a sanitized raw_response.
Sanitization reuses the core logging redactor so keys/tokens never land in DB.
"""

import logging

from django.utils import timezone

from crm.ai.domain.enums import AIMessageRole, AIRunStatus
from crm.ai.domain.value_objects import AIResponse
from crm.ai.models import AIMessage, AIRun
from crm.core.logging import sanitize

logger = logging.getLogger(__name__)

_VALID_ROLES = set(AIMessageRole.values)


class AIRunLogger:
    @staticmethod
    def start(
        *,
        organization_id,
        purpose: str,
        input_messages: list[dict],
        input_context: dict,
        prompt_version=None,
        request_id: str = "",
        correlation_id: str = "",
        **references,
    ) -> AIRun:
        """Create the AIRun in RUNNING state before touching any provider."""
        run = AIRun.objects.create(
            organization_id=organization_id,
            purpose=purpose,
            status=AIRunStatus.RUNNING,
            input_messages=sanitize(input_messages),
            input_context=sanitize(input_context),
            prompt_version=prompt_version,
            request_id=request_id or "",
            correlation_id=correlation_id or "",
            started_at=timezone.now(),
            conversation_id=references.get("conversation_id"),
            message_id=references.get("message_id"),
            contact_id=references.get("contact_id"),
            lead_id=references.get("lead_id"),
            client_id=references.get("client_id"),
            ticket_id=references.get("ticket_id"),
            task_id=references.get("task_id"),
        )
        for message in input_messages:
            role = message.get("role", "user")
            AIMessage.objects.create(
                organization_id=organization_id,
                ai_run=run,
                role=role if role in _VALID_ROLES else AIMessageRole.USER,
                content=str(message.get("content", ""))[:20000],
            )
        return run

    @staticmethod
    def record_response(run: AIRun, response: AIResponse) -> None:
        run.provider = response.provider
        run.model = response.model
        run.output_text = response.text or response.transcription_text
        run.output_json = sanitize(response.json) if response.json is not None else None
        run.raw_response = sanitize(response.raw_response or {})
        run.tool_calls = [
            {"tool_name": call.tool_name, "arguments": sanitize(call.arguments)}
            for call in response.tool_calls
        ]
        run.usage_input_tokens = response.usage.input_tokens
        run.usage_output_tokens = response.usage.output_tokens
        run.usage_total_tokens = response.usage.total_tokens
        run.latency_ms = response.latency_ms
        if response.text or response.transcription_text:
            AIMessage.objects.create(
                organization_id=run.organization_id,
                ai_run=run,
                role=AIMessageRole.ASSISTANT,
                content=(response.text or response.transcription_text)[:20000],
                token_count=response.usage.output_tokens,
            )

    @staticmethod
    def finish(run: AIRun, *, status: str, error_code: str = "", error_message: str = "") -> AIRun:
        run.status = status
        run.error_code = error_code[:64]
        run.error_message = error_message[:4000]
        run.finished_at = timezone.now()
        run.save()
        logger.info(
            "AI run finished",
            extra={
                "event": "ai.run_finished",
                "organization_id": str(run.organization_id) if run.organization_id else None,
                "metadata": {
                    "run_id": str(run.id),
                    "purpose": run.purpose,
                    "status": run.status,
                    "provider": run.provider,
                    "model": run.model,
                    "latency_ms": run.latency_ms,
                    "estimated_cost": str(run.estimated_cost),
                },
            },
        )
        _record_observability(run)
        return run


def _record_observability(run: AIRun) -> None:
    try:
        from crm.ai.domain.enums import AIRunStatus
        from crm.audit.services import AIDecisionLogger, ExternalRequestLogger

        if run.status in {
            AIRunStatus.SUCCESS.value,
            AIRunStatus.FALLBACK_USED.value,
            AIRunStatus.SCHEMA_INVALID.value,
            AIRunStatus.BLOCKED_BY_SAFETY.value,
        }:
            AIDecisionLogger.log_from_run(ai_run=run, decision_type=run.purpose)
        elif run.status == AIRunStatus.FAILED.value:
            ExternalRequestLogger.log(
                organization=run.organization_id,
                provider=run.provider or "ai",
                service="ai",
                operation=run.purpose,
                success=False,
                error_code=run.error_code,
                error_message=run.error_message,
                request_metadata={
                    "ai_run_id": str(run.id),
                    "model": run.model,
                    "request_id": run.request_id,
                },
            )
    except Exception:
        logger.exception(
            "Failed to record AI observability",
            extra={
                "event": "ai.observability_record_failed",
                "metadata": {"ai_run_id": str(run.id)},
            },
        )
