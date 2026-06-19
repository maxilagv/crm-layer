from typing import ClassVar

from pydantic import Field

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


@register_schema(AIPurpose.EMBEDDING.value)
class EmbeddingSchema(AISchema):
    vector: list[float] = Field(default_factory=list)
    model: str = ""

    example: ClassVar[dict] = {"vector": [0.1, 0.2, 0.3], "model": "fake-embedding"}
