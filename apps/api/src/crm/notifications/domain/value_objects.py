from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryDecision:
    allowed: bool
    reason: str = ""
