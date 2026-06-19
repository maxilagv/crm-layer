"""create_call_request: persists a call request via the outbox.

Consumed in a later phase (calendar/agenda). Deferred real action, not a fake
success.
"""

from crm.ai.domain.enums import AIPurpose, RiskLevel
from crm.ai.domain.events import EVENT_AI_CALL_REQUESTED
from crm.core.services.outbox import create_outbox_event

from .base import BaseTool, ToolContext, ToolDefinition
from .responses import deferred


class CreateCallRequestTool(BaseTool):
    definition = ToolDefinition(
        name="create_call_request",
        version="1",
        description="Registra que el lead/cliente pidió una llamada.",
        argument_schema={
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "properties": {
                "preferred_time": {"type": ["string", "null"]},
                "notes": {"type": "string"},
            },
        },
        permissions_required=(),
        allowed_purposes=(AIPurpose.SALES_REPLY.value, AIPurpose.SUPPORT_REPLY.value),
        side_effects="Evento outbox ai.call_request_created.v1",
        idempotency_scope=("preferred_time",),
        audit_event="ai_tool_create_call_request",
        risk_level=RiskLevel.LOW.value,
    )

    def execute(self, *, arguments, context: ToolContext) -> dict:
        event = create_outbox_event(
            event_type=EVENT_AI_CALL_REQUESTED,
            organization_id=context.organization_id,
            payload={
                "event_type": EVENT_AI_CALL_REQUESTED,
                "organization_id": str(context.organization_id),
                "data": {
                    "preferred_time": arguments.get("preferred_time"),
                    "notes": arguments.get("notes", "")[:500],
                    "conversation_id": str(context.conversation_id or "") or None,
                    "contact_id": str(context.contact_id or "") or None,
                    "ai_run_id": str(context.ai_run.id),
                },
                "metadata": {"request_id": getattr(context.request, "request_id", None)},
            },
        )
        return deferred(EVENT_AI_CALL_REQUESTED, outbox_event_id=str(event.id))
