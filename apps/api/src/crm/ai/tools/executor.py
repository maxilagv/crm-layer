"""ToolExecutor: the only path from a model's tool request to a side effect.

Pipeline: exists -> argument schema -> purpose -> permissions -> tenant ->
idempotency -> execute -> record AIToolCall -> audit. Every request leaves a
persisted AIToolCall regardless of outcome. Arguments are validated against the
tool's JSON-schema subset (type/required/enum) without extra dependencies.
"""

import hashlib
import json
import logging

from django.utils import timezone

from crm.ai.domain.enums import ToolCallStatus
from crm.ai.domain.exceptions import (
    AIError,
    AIToolPermissionDenied,
    AIToolUnavailable,
    AIToolValidationError,
)
from crm.ai.domain.value_objects import AIToolRequest, AIToolResult
from crm.ai.models import AIToolCall
from crm.audit.services import audit_event_create
from crm.core.logging import sanitize

from .base import BaseTool, ToolContext
from .permissions import ToolPermissionPolicy
from .registry import get_tool, tool_exists

logger = logging.getLogger(__name__)

_JSON_TYPES = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
}


def validate_arguments(schema: dict, arguments: dict) -> list[str]:
    """Minimal JSON-schema subset validation: required, property types, enums."""
    errors: list[str] = []
    if not isinstance(arguments, dict):
        return ["arguments must be an object"]
    properties = schema.get("properties", {})
    for required_key in schema.get("required", []):
        if required_key not in arguments:
            errors.append(f"missing required argument '{required_key}'")
    if schema.get("additionalProperties") is False:
        for key in arguments:
            if key not in properties:
                errors.append(f"unexpected argument '{key}'")
    for key, value in arguments.items():
        spec = properties.get(key)
        if not spec:
            continue
        expected = spec.get("type")
        if expected:
            types = expected if isinstance(expected, list) else [expected]
            if value is None:
                if "null" not in types:
                    errors.append(f"argument '{key}' must not be null")
                continue
            python_types: list[type] = []
            for json_type in types:
                mapped = _JSON_TYPES.get(json_type)
                if isinstance(mapped, tuple):
                    python_types.extend(mapped)
                elif mapped is not None:
                    python_types.append(mapped)
            # bool is a subclass of int in Python: reject bools for numerics.
            if python_types and (
                not isinstance(value, tuple(python_types))
                or (isinstance(value, bool) and bool not in python_types)
            ):
                errors.append(f"argument '{key}' has wrong type (expected {expected})")
                continue
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"argument '{key}' not in allowed values")
    return errors


def _idempotency_key(tool: BaseTool, arguments: dict, context: ToolContext) -> str:
    scope = tool.definition.idempotency_scope
    if not scope:
        return ""
    payload = {
        "tool": tool.definition.name,
        "org": str(context.organization_id),
        "conversation": str(context.conversation_id or ""),
        "args": {key: arguments.get(key) for key in sorted(scope)},
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


class ToolExecutor:
    @staticmethod
    def execute(*, request: AIToolRequest, context: ToolContext) -> AIToolResult:
        record = AIToolCall.objects.create(
            organization_id=context.organization_id,
            ai_run=context.ai_run,
            tool_name=request.tool_name,
            arguments=sanitize(request.arguments),
            status=ToolCallStatus.REQUESTED,
        )

        def _finish(
            status: str,
            *,
            result: dict | None = None,
            error: AIError | None = None,
            validated: dict | None = None,
        ) -> AIToolResult:
            record.status = status
            record.validated_arguments = validated
            record.result = sanitize(result) if result else None
            if error is not None:
                record.error_code = error.code
                record.error_message = str(error)[:2000]
            record.finished_at = timezone.now()
            record.save()
            return AIToolResult(
                tool_name=request.tool_name,
                status=status,
                result=result or {},
                error_code=record.error_code,
                error_message=record.error_message,
                tool_call_record_id=record.id,
            )

        # 1. Tool must exist.
        if not tool_exists(request.tool_name):
            return _finish(
                ToolCallStatus.BLOCKED,
                error=AIToolPermissionDenied(f"Tool '{request.tool_name}' is not registered"),
            )
        tool = get_tool(request.tool_name)
        record.tool_version = tool.definition.version

        # 2. Argument schema.
        problems = validate_arguments(tool.definition.argument_schema, request.arguments)
        if problems:
            return _finish(
                ToolCallStatus.FAILED,
                error=AIToolValidationError("; ".join(problems), errors=problems),
            )

        # 3-4. Purpose + permissions.
        try:
            ToolPermissionPolicy.check(tool=tool, context=context)
        except AIToolPermissionDenied as exc:
            return _finish(ToolCallStatus.BLOCKED, error=exc)

        # 5. Human approval gate (recorded, not executed).
        if tool.definition.requires_human_approval:
            return _finish(
                ToolCallStatus.SKIPPED,
                error=AIToolPermissionDenied(
                    f"Tool '{tool.definition.name}' requires human approval"
                ),
            )

        # 6. Idempotency: same scope already executed -> duplicate, no re-run.
        idempotency_key = _idempotency_key(tool, request.arguments, context)
        if idempotency_key:
            record.idempotency_key = idempotency_key
            existing = (
                AIToolCall.objects.filter(
                    organization_id=context.organization_id,
                    idempotency_key=idempotency_key,
                    status=ToolCallStatus.EXECUTED,
                )
                .exclude(id=record.id)
                .first()
            )
            if existing is not None:
                return _finish(
                    ToolCallStatus.DUPLICATE,
                    result={"duplicate_of": str(existing.id), **(existing.result or {})},
                    validated=request.arguments,
                )

        # 7-8. Execute through the internal service.
        record.status = ToolCallStatus.APPROVED
        record.started_at = timezone.now()
        record.save(
            update_fields=["status", "started_at", "tool_version", "idempotency_key", "updated_at"]
        )
        try:
            result = tool.execute(arguments=request.arguments, context=context)
        except AIToolUnavailable as exc:
            return _finish(ToolCallStatus.FAILED, error=exc, validated=request.arguments)
        except AIError as exc:
            logger.exception(
                "Tool execution failed",
                extra={"event": "ai.tool_failed", "metadata": {"tool": request.tool_name}},
            )
            return _finish(ToolCallStatus.FAILED, error=exc, validated=request.arguments)
        except Exception as exc:
            logger.exception(
                "Tool execution crashed",
                extra={"event": "ai.tool_crashed", "metadata": {"tool": request.tool_name}},
            )
            wrapped = AIError(str(exc)[:300])
            return _finish(ToolCallStatus.FAILED, error=wrapped, validated=request.arguments)

        # 9-10. Audit the side effect.
        if tool.definition.audit_event:
            audit_event_create(
                event_type=tool.definition.audit_event,
                actor=context.actor,
                organization=_org_stub(context.organization_id),
                request=context.request,
                resource_type="ai_tool_call",
                resource_id=str(record.id),
                metadata={"tool": tool.definition.name, "ai_run_id": str(context.ai_run.id)},
            )
        return _finish(ToolCallStatus.EXECUTED, result=result, validated=request.arguments)


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()
