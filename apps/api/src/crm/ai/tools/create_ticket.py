"""create_ticket: explicit stub — the support/tickets module arrives in Fase 7.

TODO(Fase 7): call the real ticket service validating the client/conversation
relationship.
"""

from crm.ai.domain.enums import AIPurpose, RiskLevel
from crm.ai.domain.exceptions import AIToolUnavailable
from crm.core.security.permissions import PermissionCode

from .base import BaseTool, ToolContext, ToolDefinition


class CreateTicketTool(BaseTool):
    definition = ToolDefinition(
        name="create_ticket",
        version="1",
        description="Crea un ticket de soporte a partir de la conversación o un audio.",
        argument_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "description"],
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "category": {
                    "type": "string",
                    "enum": ["bug", "incident", "question", "request", "billing", "other"],
                },
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
            },
        },
        permissions_required=(PermissionCode.TICKETS_MANAGE.value,),
        allowed_purposes=(
            AIPurpose.SUPPORT_REPLY.value,
            AIPurpose.AUDIO_TICKET_EXTRACTION.value,
        ),
        side_effects="Creación de ticket (módulo support: Fase 7)",
        idempotency_scope=("title",),
        audit_event="ai_tool_create_ticket",
        risk_level=RiskLevel.MEDIUM.value,
    )

    def execute(self, *, arguments, context: ToolContext) -> dict:
        raise AIToolUnavailable(
            "El módulo de tickets todavía no está implementado (Fase 7); la tool queda registrada"
        )
