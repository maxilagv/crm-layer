"""Structured schema for MEMORY_EXTRACTION (Phase 9.1).

The model reads a conversation and extracts durable, useful facts about the
contact (preferences, pain points, objections, commitments, etc.) with an
importance score. The validated output is persisted as ConversationMemory rows
and selectively injected back into future replies.
"""

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema

# Must match crm.conversations.constants.MemoryType.values exactly.
MemoryFactType = Literal[
    "preference",
    "pain_point",
    "technical_context",
    "commercial_context",
    "support_context",
    "objection",
    "commitment",
]


class MemoryFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_type: MemoryFactType
    content: str
    importance: int = Field(ge=1, le=5, default=3)
    # Null = permanent fact. Use a TTL for time-bound facts (e.g. "viaja en julio").
    expires_in_days: int | None = None


@register_schema(AIPurpose.MEMORY_EXTRACTION.value)
class MemoryExtractionSchema(AISchema):
    facts: list[MemoryFact] = Field(default_factory=list)

    example: ClassVar[dict] = {
        "facts": [
            {
                "memory_type": "preference",
                "content": "Prefiere que le escriban por la mañana.",
                "importance": 2,
                "expires_in_days": None,
            },
            {
                "memory_type": "commitment",
                "content": "Le prometimos enviar la propuesta el viernes.",
                "importance": 5,
                "expires_in_days": 14,
            },
            {
                "memory_type": "objection",
                "content": "Le preocupa el presupuesto: cree que puede ser caro.",
                "importance": 4,
                "expires_in_days": None,
            },
        ]
    }
