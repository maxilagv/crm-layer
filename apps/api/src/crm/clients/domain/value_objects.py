from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClientResolution:
    is_client: bool
    reason: str
    client_id: Any = None
    contact_id: Any = None
    support_level: str | None = None
    can_request_support: bool = False

    def as_dict(self) -> dict:
        return {
            "is_client": self.is_client,
            "client_id": str(self.client_id) if self.client_id else None,
            "contact_id": str(self.contact_id) if self.contact_id else None,
            "support_level": self.support_level,
            "can_request_support": self.can_request_support,
            "reason": self.reason,
        }

    @classmethod
    def negative(cls, reason: str, *, contact_id=None) -> "ClientResolution":
        return cls(is_client=False, reason=reason, contact_id=contact_id)
