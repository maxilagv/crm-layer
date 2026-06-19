"""send_whatsapp_message: real outbound via the Fase 4 whatsapp module.

HARD RULE: every externally-bound message passes SafetyGuard first. A blocked
reply never reaches the provider queue.
"""

import uuid

from crm.ai.domain.enums import AIPurpose, RiskLevel
from crm.ai.domain.exceptions import AISafetyBlocked, AIToolValidationError
from crm.core.security.permissions import PermissionCode

from .base import BaseTool, ToolContext, ToolDefinition
from .responses import ok


class SendWhatsAppMessageTool(BaseTool):
    definition = ToolDefinition(
        name="send_whatsapp_message",
        version="1",
        description="Envía un mensaje de WhatsApp al contacto de la conversación actual.",
        argument_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["body"],
            "properties": {"body": {"type": "string"}},
        },
        permissions_required=(PermissionCode.CONVERSATIONS_REPLY.value,),
        allowed_purposes=(AIPurpose.SALES_REPLY.value, AIPurpose.SUPPORT_REPLY.value),
        side_effects="Encola mensaje saliente real de WhatsApp",
        idempotency_scope=("body",),
        audit_event="ai_tool_send_whatsapp_message",
        risk_level=RiskLevel.HIGH.value,
    )

    def execute(self, *, arguments, context: ToolContext) -> dict:
        from crm.ai.services.safety_guard import SafetyGuard
        from crm.conversations.models import Conversation
        from crm.whatsapp.services.outbound_message_sender import queue_text_message

        if context.conversation_id is None:
            raise AIToolValidationError("send_whatsapp_message requires a conversation context")
        conversation = Conversation.objects.select_related("contact").get(
            id=context.conversation_id, organization_id=context.organization_id
        )

        safety = SafetyGuard.evaluate_reply(
            organization_id=context.organization_id,
            proposed_reply=arguments["body"],
            inbound_text="",
            purpose=context.purpose,
        )
        if not safety.allows_send:
            raise AISafetyBlocked(
                f"SafetyGuard decision '{safety.decision}': {'; '.join(safety.reasons)}",
                safety_result=safety,
            )

        body_fingerprint = uuid.uuid5(uuid.NAMESPACE_OID, arguments["body"]).hex[:16]
        result = queue_text_message(
            organization=_org_stub(context.organization_id),
            conversation=conversation,
            contact=conversation.contact,
            body=arguments["body"],
            actor=context.actor,
            request=context.request,
            idempotency_key=f"ai-run-{context.ai_run.id}-{body_fingerprint}",
        )
        return ok(outbound_message_id=str(result.outbound.id), created=result.created)


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()
