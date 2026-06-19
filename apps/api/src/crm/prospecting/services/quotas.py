"""In-app quota guards for paid prospecting providers."""

from __future__ import annotations

import logging

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

_DAY_SECONDS = 60 * 60 * 24
_MONTH_SECONDS = 60 * 60 * 24 * 32


def daily_key(source: str) -> str:
    return f"{source}:{timezone.localdate().isoformat()}"


def monthly_key(source: str) -> str:
    return f"{source}:{timezone.localdate().strftime('%Y-%m')}"


def consume_quota(source: str, quotas: list[tuple[str, int, int]]) -> bool:
    """Return True after reserving one unit in every quota bucket.

    The caller must invoke this immediately before an external API call. If a
    bucket is already at/over its limit, nothing is called and the event is logged.
    """
    for key, limit, _timeout in quotas:
        if limit <= 0:
            _log_cap(source, key, limit, 0)
            return False
        used = int(cache.get(key, 0) or 0)
        if used >= limit:
            _log_cap(source, key, limit, used)
            return False

    for key, _limit, timeout in quotas:
        cache.add(key, 0, timeout=timeout)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=timeout)
    return True


def consume_daily(source: str, limit: int) -> bool:
    return consume_quota(source, [(daily_key(source), int(limit), _DAY_SECONDS)])


def consume_monthly(source: str, limit: int) -> bool:
    return consume_quota(source, [(monthly_key(source), int(limit), _MONTH_SECONDS)])


def consume_daily_and_monthly(source: str, daily_limit: int, monthly_limit: int) -> bool:
    return consume_quota(
        source,
        [
            (daily_key(source), int(daily_limit), _DAY_SECONDS),
            (monthly_key(source), int(monthly_limit), _MONTH_SECONDS),
        ],
    )


def _log_cap(source: str, key: str, limit: int, used: int) -> None:
    logger.info(
        "Prospecting provider quota reached; skipping external call",
        extra={
            "event": "prospecting.provider_quota_reached",
            "metadata": {"source": source, "key": key, "limit": limit, "used": used},
        },
    )
