from typing import ClassVar, Literal

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema

AssistantIntent = Literal[
    "answer",
    "draft",
    "summarize",
    "plan",
    "remind",
    "lookup",
    "other",
]


@register_schema(AIPurpose.ASSISTANT_REPLY.value)
class AssistantReplySchema(AISchema):
    reply: str
    intent: AssistantIntent
    confidence: float = Field(ge=0, le=1)

    example: ClassVar[dict] = {
        "reply": (
            "Listo. Te dejo un borrador del mensaje para el cliente y, si querés, "
            "te lo paso también más formal."
        ),
        "intent": "draft",
        "confidence": 0.9,
    }
