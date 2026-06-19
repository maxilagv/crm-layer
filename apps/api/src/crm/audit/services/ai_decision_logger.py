from __future__ import annotations

from decimal import Decimal, InvalidOperation

from crm.audit.models import AuditAIDecision

from .audit_sanitizer import sanitize_payload
from .context import request_ids


class AIDecisionLogger:
    @staticmethod
    def log_from_run(
        *,
        ai_run,
        decision_type: str | None = None,
        decision: dict | None = None,
        resource_type: str = "",
        resource_id=None,
        input_summary: str = "",
        output_summary: str = "",
        request=None,
        metadata: dict | None = None,
    ) -> AuditAIDecision:
        request_id, correlation_id = request_ids(request)
        safety = ai_run.safety_result or {}
        output_json = ai_run.output_json or {}
        clean_decision = sanitize_payload(decision or output_json or {})
        return AuditAIDecision.objects.create(
            organization_id=ai_run.organization_id,
            ai_run_id=ai_run.id,
            purpose=ai_run.purpose,
            provider=ai_run.provider,
            model=ai_run.model,
            prompt_version_id=ai_run.prompt_version_id,
            decision_type=decision_type or ai_run.purpose,
            decision=clean_decision,
            risk_level=str(output_json.get("risk_level", safety.get("risk_level", ""))),
            confidence=_decimal_or_none(output_json.get("confidence")),
            input_summary=(input_summary or _summarize(ai_run.input_messages))[:2000],
            output_summary=(output_summary or ai_run.output_text or str(output_json))[:2000],
            safety_decision=str(safety.get("decision", "")),
            tool_calls_count=len(ai_run.tool_calls or []),
            blocked_reason=str(safety.get("blocked_reason", ""))[:255],
            resource_type=resource_type,
            resource_id=resource_id,
            conversation_id=ai_run.conversation_id,
            contact_id=ai_run.contact_id,
            lead_id=ai_run.lead_id,
            ticket_id=ai_run.ticket_id,
            task_id=ai_run.task_id,
            request_id=request_id or ai_run.request_id,
            correlation_id=correlation_id or ai_run.correlation_id,
            metadata=sanitize_payload(metadata or {}),
        )


def _decimal_or_none(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _summarize(messages) -> str:
    if not messages:
        return ""
    if isinstance(messages, list):
        return " ".join(str(item.get("content", item))[:300] for item in messages[:3])
    return str(messages)[:1000]


def log_ai_decision_from_run(*, ai_run, decision_type: str | None = None, **kwargs):
    return AIDecisionLogger.log_from_run(ai_run=ai_run, decision_type=decision_type, **kwargs)
