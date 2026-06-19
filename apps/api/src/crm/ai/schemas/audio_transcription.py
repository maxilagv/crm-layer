from typing import ClassVar

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


@register_schema(AIPurpose.AUDIO_TRANSCRIPTION.value)
class AudioTranscriptionSchema(AISchema):
    text: str
    language: str = "es"
    duration_seconds: float = Field(ge=0, default=0)
    confidence: float = Field(ge=0, le=1, default=0.9)

    example: ClassVar[dict] = {
        "text": "Hola, tengo un problema con el sistema de turnos.",
        "language": "es",
        "duration_seconds": 12.5,
        "confidence": 0.92,
    }
