from dataclasses import dataclass, field


@dataclass(frozen=True)
class TriageResult:
    priority: str
    category: str
    reasons: list[str] = field(default_factory=list)
    requires_owner_notification: bool = False
    suggested_status: str | None = None

    def as_dict(self) -> dict:
        return {
            "priority": self.priority,
            "category": self.category,
            "reasons": self.reasons,
            "requires_owner_notification": self.requires_owner_notification,
            "suggested_status": self.suggested_status,
        }
