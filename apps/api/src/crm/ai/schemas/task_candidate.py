from typing import ClassVar, Literal

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


class TaskCandidateSchema(AISchema):
    title: str
    description: str = ""
    due_at: str | None = None  # ISO-8601 or null
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    source_message_id: str | None = None
    related_contact_id: str | None = None
    confidence: float = Field(ge=0, le=1)
    requires_confirmation: bool = True

    example: ClassVar[dict] = {
        "title": "Enviar presupuesto a Juan",
        "description": "El lead pidió presupuesto del plan automatización WhatsApp.",
        "due_at": "2026-06-13T12:00:00-03:00",
        "priority": "high",
        "source_message_id": None,
        "related_contact_id": None,
        "confidence": 0.9,
        "requires_confirmation": True,
    }


@register_schema(AIPurpose.TASK_EXTRACTION.value)
class TaskExtractionSchema(AISchema):
    tasks: list[TaskCandidateSchema] = Field(default_factory=list)

    example: ClassVar[dict] = {"tasks": [TaskCandidateSchema.example]}
