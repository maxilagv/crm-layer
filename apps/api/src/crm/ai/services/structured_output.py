"""Validate model JSON output against the purpose schema (Pydantic v2).

Retry policy lives in the gateway: attempt 1 strict; attempt 2 sends the
validation error back as a repair instruction; on the second failure the run is
marked ``schema_invalid`` and NOTHING touches the database.
"""

from pydantic import ValidationError

from crm.ai.domain.value_objects import StructuredValidationResult
from crm.ai.schemas import schema_for_purpose


class StructuredOutputValidator:
    @staticmethod
    def validate(purpose: str, payload: dict | None) -> StructuredValidationResult:
        schema_class = schema_for_purpose(purpose)
        if schema_class is None:
            # Purposes without a registered schema accept any dict payload.
            return StructuredValidationResult(is_valid=True, data=payload or {})
        if payload is None:
            return StructuredValidationResult(
                is_valid=False, errors=["Provider returned no JSON payload"]
            )
        try:
            model = schema_class.model_validate(payload)
        except ValidationError as exc:
            errors = [
                f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in exc.errors()
            ]
            return StructuredValidationResult(is_valid=False, errors=errors)
        return StructuredValidationResult(is_valid=True, data=model.model_dump(mode="json"))

    @staticmethod
    def repair_instruction(errors: list[str]) -> str:
        listed = "\n".join(f"- {error}" for error in errors[:15])
        return (
            "Tu respuesta anterior NO cumplió el JSON Schema requerido. "
            "Corrige estos errores y responde nuevamente SOLO con el JSON válido:\n" + listed
        )
