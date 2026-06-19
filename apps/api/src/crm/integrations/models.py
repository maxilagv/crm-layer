from django.db import models

from crm.core.models import BaseModel


class ExternalRequestLog(BaseModel):
    provider = models.CharField(max_length=80)
    operation = models.CharField(max_length=120)
    status = models.CharField(max_length=32)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    request_id = models.CharField(max_length=128, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "provider", "operation"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.operation}:{self.status}"
