"""pause_conversation_ai: pauses AI on the current conversation (audited)."""

from crm.ai.domain.enums import AIPurpose, RiskLevel
from crm.ai.domain.exceptions import AIToolValidationError
from crm.core.security.permissions import PermissionCode

from .base import BaseTool, ToolContext, ToolDefinition
from .responses import ok


class PauseConversationAITool(BaseTool):
    definition = ToolDefinition(
        name="pause_conversation_ai",
        version="1",
        description="Pausa la IA en la conversación actual para que la maneje un humano.",
        argument_schema={
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "properties": {"reason": {"type": "string"}},
        },
        permissions_required=(PermissionCode.CONVERSATIONS_REPLY.value,),
        allowed_purposes=(
            AIPurpose.SALES_REPLY.value,
            AIPurpose.SUPPORT_REPLY.value,
            AIPurpose.RISK_CLASSIFICATION.value,
        ),
        side_effects="Cambia mode/ai_enabled de la conversación (auditado por handoff service)",
        idempotency_scope=(),
        audit_event="ai_tool_pause_conversation",
        risk_level=RiskLevel.LOW.value,
    )

    def execute(self, *, arguments, context: ToolContext) -> dict:
        from crm.conversations.models import Conversation
        from crm.conversations.services import ConversationHandoffService

        if context.conversation_id is None:
            raise AIToolValidationError("pause_conversation_ai requires a conversation context")
        conversation = Conversation.objects.select_related("contact").get(
            id=context.conversation_id, organization_id=context.organization_id
        )
        ConversationHandoffService.pause_ai(
            conversation=conversation, actor=context.actor, request=context.request
        )
        return ok(conversation_id=str(conversation.id), mode=conversation.mode)
