from __future__ import annotations

from datetime import timedelta

from django.db import connection
from django.utils import timezone

from crm.analytics.models import AlertEvent
from crm.audit.models import AuditExternalRequest
from crm.core.models import OutboxEvent
from crm.core.observability.metrics import MetricsRecorder


class SystemStatusBuilder:
    @staticmethod
    def build() -> dict:
        checks = {
            "database": _database_check(),
            "outbox": _outbox_check(),
            "external_requests": _external_request_check(),
            "alerts": _alerts_check(),
        }
        status = "ok" if all(check["status"] == "ok" for check in checks.values()) else "degraded"
        return {
            "status": status,
            "checks": checks,
            "metrics": MetricsRecorder.snapshot(),
            "generated_at": timezone.now().isoformat(),
        }


def _database_check() -> dict:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return {"status": "error", "message": "database unavailable"}
    return {"status": "ok"}


def _outbox_check() -> dict:
    dead = OutboxEvent.objects.filter(status=OutboxEvent.Status.DEAD_LETTER).count()
    stale = OutboxEvent.objects.filter(
        status=OutboxEvent.Status.PROCESSING,
        locked_at__lt=timezone.now() - timedelta(minutes=15),
    ).count()
    status = "ok" if dead == 0 and stale == 0 else "error"
    return {"status": status, "dead_letter": dead, "stale_processing": stale}


def _external_request_check() -> dict:
    since = timezone.now() - timedelta(minutes=15)
    failures = AuditExternalRequest.objects.filter(success=False, created_at__gte=since).count()
    return {"status": "ok" if failures == 0 else "error", "recent_failures": failures}


def _alerts_check() -> dict:
    open_alerts = AlertEvent.objects.filter(status="open").count()
    critical = AlertEvent.objects.filter(status="open", severity="critical").count()
    return {
        "status": "ok" if critical == 0 else "error",
        "open_alerts": open_alerts,
        "critical_open_alerts": critical,
    }
