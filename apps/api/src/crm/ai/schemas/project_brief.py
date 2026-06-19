"""Structured schema for PROJECT_BRIEF (Phase 9.4).

Turns a conversation with a prospect/client into a development-ready project
brief: objectives, scope, deliverables, milestones, open questions and next
steps. Owner-only / internal (no SafetyGuard).
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


class BriefMilestone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    detail: str = ""


@register_schema(AIPurpose.PROJECT_BRIEF.value)
class ProjectBriefSchema(AISchema):
    title: str
    summary: str = ""
    objectives: list[str] = Field(default_factory=list)
    scope: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    milestones: list[BriefMilestone] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    estimated_timeline: str = ""
    estimated_budget: str = ""
    next_steps: list[str] = Field(default_factory=list)

    example: ClassVar[dict] = {
        "title": "Plataforma de turnos para ACME",
        "summary": (
            "App web + backend para gestionar turnos, con panel de administración "
            "y notificaciones por WhatsApp."
        ),
        "objectives": [
            "Reducir ausencias con recordatorios automáticos.",
            "Centralizar la agenda en un solo lugar.",
        ],
        "scope": [
            "Backend a medida (API + base de datos).",
            "App web responsive con panel de administración.",
            "Integración de notificaciones por WhatsApp.",
        ],
        "deliverables": [
            "API documentada.",
            "App web en producción.",
            "Manual de uso.",
        ],
        "milestones": [
            {"name": "Etapa 1 — Backend", "detail": "Diseño técnico + API (3 semanas)."},
            {"name": "Etapa 2 — App web", "detail": "Frontend e integraciones (3 semanas)."},
            {"name": "Etapa 3 — QA y deploy", "detail": "Pruebas, ajustes y salida (1 semana)."},
        ],
        "open_questions": [
            "¿Necesitan multi-sucursal?",
            "¿Qué pasarela de pagos usan, si aplica?",
        ],
        "estimated_timeline": "7 semanas",
        "estimated_budget": "A confirmar según alcance final",
        "next_steps": [
            "Validar alcance con el cliente.",
            "Enviar propuesta formal.",
        ],
    }
