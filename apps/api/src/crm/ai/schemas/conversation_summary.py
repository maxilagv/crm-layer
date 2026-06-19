from typing import ClassVar, Literal

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


@register_schema(AIPurpose.CONVERSATION_SUMMARY.value)
class ConversationSummarySchema(AISchema):
    summary: str
    summary_type: Literal["short", "technical", "sales", "support", "daily", "handoff"] = "short"
    key_points: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    sentiment: Literal["positive", "neutral", "negative", "mixed"] = "neutral"
    confidence: float = Field(ge=0, le=1, default=0.8)

    example: ClassVar[dict] = {
        "summary": (
            "El lead consultó por automatización de WhatsApp y quedó en agendar una llamada."
        ),
        "summary_type": "short",
        "key_points": ["interesado en automatización", "pidió llamada"],
        "open_questions": ["presupuesto disponible"],
        "sentiment": "positive",
        "confidence": 0.9,
    }
