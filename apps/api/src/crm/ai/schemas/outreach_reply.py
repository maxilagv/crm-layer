"""Structured schema for OUTREACH_REPLY."""

from typing import ClassVar

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


@register_schema(AIPurpose.OUTREACH_REPLY.value)
class OutreachReplySchema(AISchema):
    message: str = Field(min_length=1, max_length=700)
    should_send: bool
    handoff: bool
    reason: str = ""

    example: ClassVar[dict] = {
        "message": (
            "Si, obvio. La idea seria arrancar por algo simple: que cuando te busquen desde el "
            "celular vean horarios, ubicacion y un boton directo para escribirte. Te puedo mandar "
            "un ejemplo concreto aplicado a tu local y lo ves sin compromiso?"
        ),
        "should_send": True,
        "handoff": False,
        "reason": "Responde la objecion y propone un micro-paso sin presionar.",
    }
