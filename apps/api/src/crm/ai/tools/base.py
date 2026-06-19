"""Tool definition base. The model REQUESTS tools; the backend decides."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolContext:
    """Execution context injected by the executor (never by the model)."""

    organization_id: Any
    ai_run: Any
    actor: Any = None
    conversation_id: Any = None
    contact_id: Any = None
    message_id: Any = None
    request: Any = None
    purpose: str = ""


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    version: str
    description: str
    argument_schema: dict[str, Any]
    permissions_required: tuple[str, ...] = ()
    allowed_purposes: tuple[str, ...] = ()
    side_effects: str = ""
    idempotency_scope: tuple[str, ...] = ()  # argument names that form the idempotency key
    audit_event: str = ""
    risk_level: str = "low"
    requires_human_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Subclasses declare a ToolDefinition and implement execute()."""

    definition: ToolDefinition

    @abstractmethod
    def execute(self, *, arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        """Run the side effect through internal services. Returns a JSON-safe dict."""

    def provider_spec(self) -> dict[str, Any]:
        """Shape sent to providers as the callable tool description."""
        return {
            "name": self.definition.name,
            "description": self.definition.description,
            "argument_schema": self.definition.argument_schema,
        }
