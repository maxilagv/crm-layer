from typing import Any, ClassVar, Literal

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema

SupportIntent = Literal[
    "answer_question",
    "collect_information",
    "acknowledge_issue",
    "propose_solution",
    "escalate",
    "other",
]


@register_schema(AIPurpose.SUPPORT_REPLY.value)
class SupportReplySchema(AISchema):
    reply: str
    intent: SupportIntent
    ticket_updates: dict[str, Any] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list)
    should_notify_owner: bool = False
    should_handoff: bool = False
    risk_level: Literal["low", "medium", "high", "critical"] = "low"
    confidence: float = Field(ge=0, le=1)

    example: ClassVar[dict] = {
        "reply": (
            "Lamento el inconveniente. "
            "¿Podrías indicarme qué mensaje de error ves y desde cuándo ocurre?"
        ),
        "intent": "collect_information",
        "ticket_updates": {},
        "missing_information": ["mensaje de error", "fecha de inicio del problema"],
        "should_notify_owner": False,
        "should_handoff": False,
        "risk_level": "low",
        "confidence": 0.88,
    }
