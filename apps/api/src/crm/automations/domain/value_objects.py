from dataclasses import dataclass


@dataclass(frozen=True)
class ConditionResult:
    passed: bool
    reason: str


@dataclass(frozen=True)
class ActionResult:
    success: bool
    result: dict
    error_code: str = ""
    error_message: str = ""
