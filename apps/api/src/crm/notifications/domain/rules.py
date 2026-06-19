from datetime import time


def is_quiet_hours(now_time: time, start: time | None, end: time | None) -> bool:
    if start is None or end is None:
        return False
    if start == end:
        return False
    if start < end:
        return start <= now_time < end
    return now_time >= start or now_time < end


def build_deduplication_key(*, notification_type: str, resource_type: str, resource_id) -> str:
    if not resource_type or not resource_id:
        return ""
    return f"{notification_type}:{resource_type}:{resource_id}"
