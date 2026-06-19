from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.utils import timezone


def day_bounds(day: date) -> tuple[datetime, datetime]:
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    return start, start + timedelta(days=1)


def default_period(days: int = 30) -> tuple[date, date]:
    today = timezone.localdate()
    return today - timedelta(days=days - 1), today


def iter_days(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)
