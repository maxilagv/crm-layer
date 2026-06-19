from typing import Any, ClassVar, Literal

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema

SalesIntent = Literal[
    "answer_question",
    "qualify_lead",
    "handle_objection",
    "propose_call",
    "book_call",
    "send_information",
    "close_deal",
    "other",
]


@register_schema(AIPurpose.SALES_REPLY.value)
class SalesReplySchema(AISchema):
    reply: str
    intent: SalesIntent
    lead_updates: dict[str, Any] = Field(default_factory=dict)
    suggested_tasks: list[dict[str, Any]] = Field(default_factory=list)
    should_notify_owner: bool = False
    should_handoff: bool = False
    should_create_call_request: bool = False
    risk_level: Literal["low", "medium", "high", "critical"] = "low"
    confidence: float = Field(ge=0, le=1)

    example: ClassVar[dict] = {
        "reply": (
            "¡Hola! Gracias por escribirnos. "
            "¿Te parece coordinar una llamada breve para entender tu caso?"
        ),
        "intent": "propose_call",
        "lead_updates": {},
        "suggested_tasks": [],
        "should_notify_owner": False,
        "should_handoff": False,
        "should_create_call_request": True,
        "risk_level": "low",
        "confidence": 0.91,
    }
