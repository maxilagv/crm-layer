from typing import ClassVar, Literal

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


@register_schema(AIPurpose.AUDIO_TICKET_EXTRACTION.value)
class SupportTicketSchema(AISchema):
    title: str
    description: str
    category: Literal["bug", "incident", "question", "request", "billing", "other"] = "other"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    missing_information: list[str] = Field(default_factory=list)
    suggested_reply: str = ""
    owner_summary: str = ""
    confidence: float = Field(ge=0, le=1)

    example: ClassVar[dict] = {
        "title": "Error al cargar turnos",
        "description": "El cliente reporta por audio que el sistema de turnos no carga desde ayer.",
        "category": "incident",
        "priority": "high",
        "missing_information": ["navegador utilizado"],
        "suggested_reply": "Gracias por avisarnos. Estamos revisando el problema de turnos.",
        "owner_summary": "Cliente con turnos caídos desde ayer; pide solución urgente.",
        "confidence": 0.85,
    }
