from dataclasses import dataclass


@dataclass(frozen=True)
class LeadCreationResult:
    lead: object | None
    created: bool
    reason: str = ""


@dataclass(frozen=True)
class LeadScoreResult:
    lead: object
    snapshot: object | None
    updated: bool
    ai_run_id: object | None = None
    reason: str = ""
