"""Schema registry base.

Free text answers users; validated JSON touches the database. Every purpose
whose output mutates state registers a Pydantic v2 model here, and each model
ships an example used by FakeAIProvider and the evals.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class AISchema(BaseModel):
    """Strict base: unknown fields are rejected (hallucinated keys fail fast)."""

    model_config = ConfigDict(extra="forbid")

    example: ClassVar[dict] = {}


_SCHEMA_REGISTRY: dict[str, type[AISchema]] = {}


def register_schema(purpose: str):
    def decorator(schema_class: type[AISchema]) -> type[AISchema]:
        _SCHEMA_REGISTRY[purpose] = schema_class
        return schema_class

    return decorator


def schema_for_purpose(purpose: str) -> type[AISchema] | None:
    return _SCHEMA_REGISTRY.get(purpose)


def json_schema_for_purpose(purpose: str) -> dict | None:
    schema_class = schema_for_purpose(purpose)
    return schema_class.model_json_schema() if schema_class else None


def example_output_for_purpose(purpose: str) -> dict:
    schema_class = schema_for_purpose(purpose)
    return dict(schema_class.example) if schema_class else {"text": "ok"}
