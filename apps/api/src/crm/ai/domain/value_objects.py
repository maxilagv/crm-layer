"""Internal value objects exchanged between gateway, providers and services.

These are plain dataclasses: no Django models and no SDK types cross this
boundary. ``AIRequest`` travels into providers; ``AIResponse`` travels out.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .enums import RiskLevel, SafetyDecision


@dataclass(frozen=True)
class AIUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    audio_seconds: Decimal = Decimal("0")
    image_count: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class AIToolRequest:
    """A tool the model asked for. The backend decides whether it runs."""

    tool_name: str
    arguments: dict[str, Any]
    call_id: str = ""


@dataclass(frozen=True)
class AIToolResult:
    tool_name: str
    status: str
    result: dict[str, Any] = field(default_factory=dict)
    error_code: str = ""
    error_message: str = ""
    tool_call_record_id: uuid.UUID | None = None


@dataclass(frozen=True)
class RenderedPrompt:
    system_prompt: str
    developer_prompt: str
    user_content: str
    prompt_version_id: uuid.UUID | None
    output_schema: dict[str, Any] | None = None
    variables_used: dict[str, Any] = field(default_factory=dict)

    def as_messages(self) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        if self.developer_prompt:
            messages.append({"role": "developer", "content": self.developer_prompt})
        if self.user_content:
            messages.append({"role": "user", "content": self.user_content})
        return messages


@dataclass(frozen=True)
class StructuredValidationResult:
    is_valid: bool
    data: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SafetyResult:
    decision: str = SafetyDecision.SEND.value
    risk_level: str = RiskLevel.LOW.value
    reasons: list[str] = field(default_factory=list)
    blocked_phrases: list[str] = field(default_factory=list)
    policy_violations: list[str] = field(default_factory=list)
    requires_handoff: bool = False
    safe_reply_override: str = ""
    owner_notification_required: bool = False
    confidence: float = 1.0

    @property
    def allows_send(self) -> bool:
        return self.decision == SafetyDecision.SEND.value

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "risk_level": self.risk_level,
            "reasons": self.reasons,
            "blocked_phrases": self.blocked_phrases,
            "policy_violations": self.policy_violations,
            "requires_handoff": self.requires_handoff,
            "safe_reply_override": self.safe_reply_override,
            "owner_notification_required": self.owner_notification_required,
            "confidence": self.confidence,
        }


@dataclass
class AIRequest:
    """Provider-agnostic request. Built by the gateway, consumed by providers."""

    organization_id: uuid.UUID
    purpose: str
    input_messages: list[dict[str, str]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    expected_schema: dict[str, Any] | None = None
    allowed_tools: list[dict[str, Any]] = field(default_factory=list)
    model_preferences: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    correlation_id: str | None = None
    # Media inputs (transcription / image generation / embeddings).
    audio_bytes: bytes | None = None
    audio_format: str = ""
    image_prompt: str = ""
    embedding_input: str = ""


@dataclass
class AIResponse:
    """Provider-agnostic response. Providers must normalize into this shape."""

    text: str = ""
    json: dict[str, Any] | None = None
    tool_calls: list[AIToolRequest] = field(default_factory=list)
    usage: AIUsage = field(default_factory=AIUsage)
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    raw_response: dict[str, Any] = field(default_factory=dict)
    finish_reason: str = ""
    safety_result: SafetyResult | None = None
    # Media outputs.
    transcription_text: str = ""
    image_b64: str = ""
    image_url: str = ""
    embedding_vector: list[float] = field(default_factory=list)
