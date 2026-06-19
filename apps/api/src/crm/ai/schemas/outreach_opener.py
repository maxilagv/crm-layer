"""Structured schema for OUTREACH_OPENER."""

from typing import ClassVar

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


@register_schema(AIPurpose.OUTREACH_OPENER.value)
class OutreachOpenerSchema(AISchema):
    message: str = Field(min_length=1, max_length=520)
    references_signal: str

    example: ClassVar[dict] = {
        "message": (
            "Hola! Soy Martin, armo webs simples para negocios de barrio. Te encontre buscando "
            "gomerias en la zona y vi que no tenes una pagina propia donde te ubiquen con horarios "
            "y direccion. Te preparo una idea de como te quedaria, sin compromiso. Te la muestro "
            "por aca? Si no te sirve, decime y listo."
        ),
        "references_signal": "no_website",
    }
