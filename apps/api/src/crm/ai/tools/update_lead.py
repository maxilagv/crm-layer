"""update_lead: explicit stub — the leads module does not exist until Fase 6.

It fails with a controlled, auditable error instead of simulating success.
TODO(Fase 6): replace the body with crm.leads service calls validating the
allowed-fields whitelist below.
"""

from crm.ai.domain.enums import AIPurpose, RiskLevel
from crm.ai.domain.exceptions import AIToolUnavailable, AIToolValidationError
from crm.core.security.permissions import PermissionCode

from .base import BaseTool, ToolContext, ToolDefinition

ALLOWED_LEAD_FIELDS = {"stage", "temperature", "score", "next_best_action", "notes"}


class UpdateLeadTool(BaseTool):
    definition = ToolDefinition(
        name="update_lead",
        version="1",
        description="Actualiza campos permitidos de un lead (stage, score, próxima acción).",
        argument_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["lead_id", "updates"],
            "properties": {
                "lead_id": {"type": "string"},
                "updates": {"type": "object"},
            },
        },
        permissions_required=(PermissionCode.LEADS_UPDATE.value,),
        allowed_purposes=(AIPurpose.SALES_REPLY.value, AIPurpose.LEAD_SCORING.value),
        side_effects="Mutación de lead (módulo leads: Fase 6)",
        idempotency_scope=(),
        audit_event="ai_tool_update_lead",
        risk_level=RiskLevel.MEDIUM.value,
    )

    def execute(self, *, arguments, context: ToolContext) -> dict:
        invalid = set(arguments.get("updates", {})) - ALLOWED_LEAD_FIELDS
        if invalid:
            raise AIToolValidationError(
                f"Fields not allowed for lead update: {', '.join(sorted(invalid))}"
            )
        raise AIToolUnavailable(
            "El módulo de leads todavía no está implementado (Fase 6); la tool queda registrada"
        )
