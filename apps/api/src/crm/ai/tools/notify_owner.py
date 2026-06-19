"""notify_owner: persists an owner notification request via the outbox.

Phase 8 (notifications) consumes ``ai.owner_notification_requested.v1``. The
idempotency scope (reason + conversation) prevents notification spam from
repeated model requests in the same conversation.
"""

from crm.ai.domain.enums import AIPurpose, RiskLevel
from crm.ai.domain.events import EVENT_AI_OWNER_NOTIFICATION
from crm.core.services.outbox import create_outbox_event

from .base import BaseTool, ToolContext, ToolDefinition
from .responses import deferred


class NotifyOwnerTool(BaseTool):
    definition = ToolDefinition(
        name="notify_owner",
        version="1",
        description="Notifica al dueño del negocio sobre algo que requiere su atención.",
        argument_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["reason"],
            "properties": {
                "reason": {"type": "string"},
                "urgency": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
            },
        },
        permissions_required=(),
        allowed_purposes=(
            AIPurpose.SALES_REPLY.value,
            AIPurpose.SUPPORT_REPLY.value,
            AIPurpose.RISK_CLASSIFICATION.value,
            AIPurpose.AUDIO_TICKET_EXTRACTION.value,
        ),
        side_effects="Evento outbox ai.owner_notification_requested.v1 (notificaciones: Fase 8)",
        idempotency_scope=("reason",),
        audit_event="ai_tool_notify_owner",
        risk_level=RiskLevel.LOW.value,
    )

    def execute(self, *, arguments, context: ToolContext) -> dict:
        event = create_outbox_event(
            event_type=EVENT_AI_OWNER_NOTIFICATION,
            organization_id=context.organization_id,
            payload={
                "event_type": EVENT_AI_OWNER_NOTIFICATION,
                "organization_id": str(context.organization_id),
                "data": {
                    "reason": arguments["reason"][:500],
                    "urgency": arguments.get("urgency", "medium"),
                    "conversation_id": str(context.conversation_id or "") or None,
                    "ai_run_id": str(context.ai_run.id),
                },
                "metadata": {"request_id": getattr(context.request, "request_id", None)},
            },
        )
        return deferred(EVENT_AI_OWNER_NOTIFICATION, outbox_event_id=str(event.id))
