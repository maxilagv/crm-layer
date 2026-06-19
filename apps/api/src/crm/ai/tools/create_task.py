"""create_task: persists a task candidate as an outbox event.

The tasks module arrives in Phase 8; until then the candidate is a REAL
persisted event (``ai.task_candidate_created.v1``) that Phase 8 will consume.
This is a deferred action, not a simulated success.
"""

from crm.ai.domain.enums import AIPurpose, RiskLevel
from crm.ai.domain.events import EVENT_AI_TASK_CANDIDATE
from crm.core.security.permissions import PermissionCode
from crm.core.services.outbox import create_outbox_event

from .base import BaseTool, ToolContext, ToolDefinition
from .responses import deferred


class CreateTaskTool(BaseTool):
    definition = ToolDefinition(
        name="create_task",
        version="1",
        description="Crea una tarea interna para el equipo (recordatorio, seguimiento, acción).",
        argument_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["title"],
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "due_at": {"type": ["string", "null"]},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
            },
        },
        permissions_required=(PermissionCode.TASKS_MANAGE.value,),
        allowed_purposes=(
            AIPurpose.SALES_REPLY.value,
            AIPurpose.SUPPORT_REPLY.value,
            AIPurpose.TASK_EXTRACTION.value,
        ),
        side_effects="Crea evento outbox ai.task_candidate_created.v1 (módulo tasks: Fase 8)",
        idempotency_scope=("title", "due_at"),
        audit_event="ai_tool_create_task",
        risk_level=RiskLevel.LOW.value,
    )

    def execute(self, *, arguments, context: ToolContext) -> dict:
        event = create_outbox_event(
            event_type=EVENT_AI_TASK_CANDIDATE,
            organization_id=context.organization_id,
            payload={
                "event_type": EVENT_AI_TASK_CANDIDATE,
                "organization_id": str(context.organization_id),
                "data": {
                    "title": arguments["title"],
                    "description": arguments.get("description", ""),
                    "due_at": arguments.get("due_at"),
                    "priority": arguments.get("priority", "medium"),
                    "conversation_id": str(context.conversation_id or "") or None,
                    "contact_id": str(context.contact_id or "") or None,
                    "ai_run_id": str(context.ai_run.id),
                },
                "metadata": {"request_id": getattr(context.request, "request_id", None)},
            },
        )
        return deferred(EVENT_AI_TASK_CANDIDATE, outbox_event_id=str(event.id))
