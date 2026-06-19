from dataclasses import dataclass, field


@dataclass(frozen=True)
class SalesPolicyVerdict:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    sanitized_reply: str = ""


@dataclass(frozen=True)
class SalesAgentResult:
    reply: str
    intent: str
    lead: object | None
    ai_run_id: object | None
    sent_to_gateway: bool = False
    blocked: bool = False
    reasons: list[str] = field(default_factory=list)
