import re
import unicodedata
from datetime import timedelta

from django.utils import timezone

from .enums import TERMINAL_TASK_STATUSES, TaskCommandType, TaskPriority, TaskStatus

MAX_SNOOZE_COUNT = 3


def normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title or "")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized).strip().lower()
    return re.sub(r"\s+", " ", normalized)[:255]


def can_send_reminder(task) -> bool:
    return task.status not in TERMINAL_TASK_STATUSES


def should_mark_overdue(task, *, now=None) -> bool:
    now = now or timezone.now()
    return bool(task.due_at and task.due_at < now and task.status not in TERMINAL_TASK_STATUSES)


def clamp_priority(priority: str) -> str:
    return priority if priority in TaskPriority.values else TaskPriority.MEDIUM.value


def completed_at_for_status(status: str):
    return timezone.now() if status == TaskStatus.COMPLETED.value else None


def parse_command(text: str, *, now=None) -> dict:
    now = now or timezone.now()
    raw = (text or "").strip()
    normalized = normalize_title(raw).upper()
    if normalized == "HECHO":
        return {"type": TaskCommandType.COMPLETE.value}
    if normalized == "PENDIENTE":
        return {"type": TaskCommandType.PENDING.value}
    if normalized == "CANCELAR":
        return {"type": TaskCommandType.CANCEL.value}
    if normalized == "DETALLE":
        return {"type": TaskCommandType.DETAIL.value}

    postpone = re.match(r"^POSPONER\s+(\d+)\s*([HD])$", normalized)
    if postpone:
        amount = int(postpone.group(1))
        unit = postpone.group(2)
        delta = timedelta(hours=amount) if unit == "H" else timedelta(days=amount)
        return {
            "type": TaskCommandType.SNOOZE.value,
            "snooze_until": (now + delta).isoformat(),
            "amount": amount,
            "unit": unit.lower(),
        }

    tomorrow = re.match(r"^(MANANA|MAÑANA)\s+(\d{1,2})(?::(\d{2}))?$", raw.strip(), re.I)
    if tomorrow:
        hour = int(tomorrow.group(2))
        minute = int(tomorrow.group(3) or 0)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            target = (now + timedelta(days=1)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            return {"type": TaskCommandType.SNOOZE.value, "snooze_until": target.isoformat()}

    return {"type": TaskCommandType.UNKNOWN.value}
