"""Structured schema for PROSPECT_QUALIFICATION."""

from typing import ClassVar

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


@register_schema(AIPurpose.PROSPECT_QUALIFICATION.value)
class ProspectQualificationSchema(AISchema):
    fit_score: int = Field(ge=0, le=100)
    qualified: bool
    signals: list[str] = Field(default_factory=list)
    reasoning: str = ""
    recommended_angle: str = ""
    confidence: float = Field(default=0.7, ge=0, le=1)

    example: ClassVar[dict] = {
        "fit_score": 78,
        "qualified": True,
        "signals": ["no_website", "few_photos", "strong_reviews"],
        "reasoning": (
            "Tiene demanda (buen rating y reviews que siguen llegando) pero depende de canales "
            "offline: sin web y con pocas fotos. Es un negocio que funciona y le falta presencia."
        ),
        "recommended_angle": (
            "Mostrarle una web simple con reservas para captar a los que hoy lo buscan "
            "en Google y no lo encuentran."
        ),
        "confidence": 0.8,
    }
