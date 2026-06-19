"""Structured schema for DOCUMENT_DRAFT.

The model drafts a complete, professional document payload from a free-text
request. Its shape mirrors exactly what ``crm.documents.domain.payload``'s
``normalize_payload()`` consumes, so the validated output can be passed straight
to ``DocumentService.generate(payload=...)``. Numbers are plain (no thousands
separators); ``normalize_payload`` converts them to Decimals and computes totals.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


class DraftClient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    contact: str = ""
    email: str = ""
    phone: str = ""
    tax_id: str = ""
    address: str = ""


class DraftSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = ""
    body: str = ""


class DraftItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    quantity: float = 1
    unit: str = ""
    unit_price: float = 0


class DraftMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_number: str = ""


@register_schema(AIPurpose.DOCUMENT_DRAFT.value)
class DocumentDraftSchema(AISchema):
    title: str
    subtitle: str = ""
    client: DraftClient = Field(default_factory=DraftClient)
    intro: str = ""
    sections: list[DraftSection] = Field(default_factory=list)
    items: list[DraftItem] = Field(default_factory=list)
    currency: str = ""
    tax_rate: float = 0
    notes: str = ""
    terms: str = ""
    valid_until: str = ""
    meta: DraftMeta = Field(default_factory=DraftMeta)

    example: ClassVar[dict] = {
        "title": "Propuesta de desarrollo — Plataforma de turnos",
        "subtitle": "App web + backend para ACME SRL",
        "client": {
            "name": "ACME SRL",
            "contact": "Juan Pérez",
            "email": "juan@acme.com",
            "phone": "",
            "tax_id": "",
            "address": "",
        },
        "intro": (
            "Gracias por la oportunidad de trabajar juntos. A continuación detallamos "
            "el alcance, el cronograma y la inversión propuesta."
        ),
        "sections": [
            {
                "heading": "Alcance",
                "body": (
                    "Backend a medida con API documentada, app web responsive y panel "
                    "de administración, integración de notificaciones por WhatsApp y "
                    "puesta en producción."
                ),
            },
            {
                "heading": "Cronograma",
                "body": (
                    "Etapa 1: backend (3 semanas). Etapa 2: app web (3 semanas). "
                    "Etapa 3: QA y deploy (1 semana)."
                ),
            },
        ],
        "items": [
            {
                "description": "Desarrollo backend a medida (API + base de datos)",
                "quantity": 1,
                "unit": "proyecto",
                "unit_price": 1500000,
            },
            {
                "description": "App web responsive + panel de administración",
                "quantity": 1,
                "unit": "proyecto",
                "unit_price": 1200000,
            },
            {
                "description": "Soporte y mantenimiento mensual",
                "quantity": 3,
                "unit": "mes",
                "unit_price": 180000,
            },
        ],
        "currency": "ARS",
        "tax_rate": 21,
        "notes": "",
        "terms": "50% para iniciar y 50% contra entrega final.",
        "valid_until": "2026-07-15",
        "meta": {"document_number": "P-0001"},
    }
