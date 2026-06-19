from typing import ClassVar, Literal

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


@register_schema(AIPurpose.RISK_CLASSIFICATION.value)
class ModerationResultSchema(AISchema):
    risk_level: Literal["low", "medium", "high", "critical"]
    decision: Literal[
        "send",
        "revise",
        "ask_clarifying_question",
        "handoff_to_human",
        "do_not_reply",
        "notify_owner",
    ]
    reasons: list[str] = Field(default_factory=list)
    policy_violations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)

    example: ClassVar[dict] = {
        "risk_level": "low",
        "decision": "send",
        "reasons": [],
        "policy_violations": [],
        "confidence": 0.95,
    }
