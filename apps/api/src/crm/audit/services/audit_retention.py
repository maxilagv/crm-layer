from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from crm.audit.models import (
    AuditAIDecision,
    AuditDataAccessLog,
    AuditExternalRequest,
    AuditLog,
    AuditSecurityEvent,
)


class AuditRetentionService:
    @staticmethod
    def compact_old_logs(*, days: int | None = None) -> dict[str, int]:
        retention_days = days or getattr(settings, "AUDIT_RETENTION_DAYS", 0)
        if not retention_days:
            return {"soft_deleted": 0, "retention_days": 0}
        threshold = timezone.now() - timedelta(days=retention_days)
        total = 0
        for model in (
            AuditLog,
            AuditDataAccessLog,
            AuditSecurityEvent,
            AuditAIDecision,
            AuditExternalRequest,
        ):
            total += model.objects.filter(created_at__lt=threshold).update(
                deleted_at=timezone.now()
            )
        return {"soft_deleted": total, "retention_days": retention_days}
