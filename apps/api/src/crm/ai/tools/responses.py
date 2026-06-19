"""Helpers to build JSON-safe tool results."""

from typing import Any


def ok(**payload: Any) -> dict[str, Any]:
    return {"ok": True, **payload}


def deferred(event_type: str, **payload: Any) -> dict[str, Any]:
    """Side effect persisted as an outbox event for a later-phase consumer."""
    return {"ok": True, "deferred_via_outbox": True, "event_type": event_type, **payload}
