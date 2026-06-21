"""Structured schema for OUTREACH_EMAIL."""

from typing import ClassVar

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


@register_schema(AIPurpose.OUTREACH_EMAIL.value)
class OutreachEmailSchema(AISchema):
    subject: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=3000)
    references_signal: str

    example: ClassVar[dict] = {
        "subject": "Idea simple para que te encuentren online",
        "body": (
            "Hola, vi que tu negocio podria captar mejor a la gente que busca desde el celular. "
            "Te puedo preparar una propuesta corta con horarios, ubicacion y contacto directo, "
            "sin compromiso. Si te sirve, coordinamos 10 minutos esta semana."
        ),
        "references_signal": "no_website",
    }
