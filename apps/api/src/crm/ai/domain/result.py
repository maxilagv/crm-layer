"""Semantic result returned by AIGateway to business modules.

Business code never sees raw provider responses: it receives an
``AIGatewayResult`` referencing the persisted ``AIRun`` plus validated output.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from .value_objects import AIToolResult, SafetyResult


@dataclass(frozen=True)
class AIGatewayResult:
    # None only for purely deterministic verdicts that made no provider call.
    run_id: uuid.UUID | None
    status: str
    purpose: str
    text: str = ""
    data: dict[str, Any] | None = None
    safety: SafetyResult | None = None
    tool_results: list[AIToolResult] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    error_code: str = ""
    error_message: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status in {"success", "fallback_used"}

    @property
    def can_send_reply(self) -> bool:
        return self.succeeded and (self.safety is None or self.safety.allows_send)
