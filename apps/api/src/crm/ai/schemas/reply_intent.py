"""Structured schema for REPLY_INTENT."""

from typing import ClassVar, Literal

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema

ReplyIntent = Literal["interested", "not_interested", "maybe", "do_not_contact", "unclear"]
NextAction = Literal[
    "ask_qualifying",
    "propose_call",
    "send_info",
    "rebut_objection",
    "schedule_followup",
    "handoff_human",
    "none",
]


@register_schema(AIPurpose.REPLY_INTENT.value)
class ReplyIntentSchema(AISchema):
    intent: ReplyIntent
    confidence: float = Field(ge=0, le=1)
    reasoning: str = ""
    next_action: NextAction = "none"
    objection_type: str = ""

    example: ClassVar[dict] = {
        "intent": "interested",
        "confidence": 0.82,
        "reasoning": "Pidio mas informacion y no expreso rechazo.",
        "next_action": "send_info",
        "objection_type": "",
    }
