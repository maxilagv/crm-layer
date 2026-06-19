from typing import ClassVar, Literal

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


@register_schema(AIPurpose.LEAD_SCORING.value)
class LeadScoreSchema(AISchema):
    score: int = Field(ge=0, le=100)
    temperature: Literal["cold", "warm", "hot", "critical"]
    pain_points: list[str] = Field(default_factory=list)
    urgency: Literal["low", "medium", "high", "unknown"]
    budget_signal: Literal["none", "unknown", "low", "medium", "high", "confirmed"]
    authority_signal: Literal["unknown", "influencer", "decision_maker", "likely_decision_maker"]
    business_fit: Literal["low", "medium", "high"]
    technical_match: Literal["low", "medium", "high"]
    risk_penalty: int = Field(ge=0, le=100, default=0)
    next_best_action: str
    confidence: float = Field(ge=0, le=1)
    reasoning_summary: str

    example: ClassVar[dict] = {
        "score": 82,
        "temperature": "hot",
        "pain_points": ["pierde leads por demora", "necesita automatizar WhatsApp"],
        "urgency": "high",
        "budget_signal": "unknown",
        "authority_signal": "likely_decision_maker",
        "business_fit": "high",
        "technical_match": "high",
        "risk_penalty": 0,
        "next_best_action": "propose_call",
        "confidence": 0.87,
        "reasoning_summary": "Lead con dolor claro y urgencia alta; falta validar presupuesto.",
    }
