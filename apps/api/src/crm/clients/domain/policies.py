"""Client routing policy (conservative, overridable later via settings)."""

from .enums import SUPPORT_ROUTABLE_STATUSES


def status_is_support_routable(status: str) -> bool:
    return status in {s.value for s in SUPPORT_ROUTABLE_STATUSES}
