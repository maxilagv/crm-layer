"""Pure support rules."""

import unicodedata

from .enums import TicketPriority, TicketStatus

_RESOLVABLE_BLOCKED_FOR_AI = {TicketPriority.CRITICAL.value}
_REOPENABLE_FROM = {TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value}


def normalize(text: str) -> str:
    """Lowercase + strip accents for keyword matching."""
    lowered = (text or "").lower()
    return "".join(
        c for c in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(c)
    )


def ai_may_resolve(priority: str) -> bool:
    return priority not in _RESOLVABLE_BLOCKED_FOR_AI


def can_reopen(status: str) -> bool:
    return status in _REOPENABLE_FROM
