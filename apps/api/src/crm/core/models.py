import uuid
from datetime import timedelta
from typing import Any

from django.db import models
from django.utils import timezone

OUTBOX_BACKOFF_CAP_SECONDS = 300


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)

    def soft_delete(self):
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def delete(self):
        return self.soft_delete()


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Default manager: hides soft-deleted rows. Use ``all_objects`` to include them."""

    def get_queryset(self):
        return super().get_queryset().alive()


class BaseModel(models.Model):
    """Common base for all main models: UUID pk, tenancy, audit stamps, soft delete."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
        ]

    def soft_delete(self, *, save: bool = True) -> None:
        self.deleted_at = timezone.now()
        if save:
            self.save(update_fields=["deleted_at", "updated_at"])

    def restore(self, *, save: bool = True) -> None:
        self.deleted_at = None
        if save:
            self.save(update_fields=["deleted_at", "updated_at"])


class IdempotencyKey(BaseModel):
    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"

    key = models.CharField(max_length=255)
    scope = models.CharField(max_length=120)
    request_hash = models.CharField(max_length=128)
    response_body = models.JSONField(null=True, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PROCESSING)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "core_idempotency_key"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "scope", "key"],
                name="uniq_idempotency_org_scope_key",
                # Two NULL organization_ids still collide: pre-tenant keys are global.
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["status", "expires_at"]),
        ]

    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    def __str__(self) -> str:
        return f"{self.scope}:{self.key}"


class OutboxEvent(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        DEAD_LETTER = "dead_letter", "Dead letter"

    event_type = models.CharField(max_length=255)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "core_outbox_event"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["status", "available_at"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["organization_id", "status"]),
        ]

    def mark_processed(self) -> None:
        self.status = self.Status.PROCESSED
        self.processed_at = timezone.now()
        self.locked_at = None
        self.error_message = ""
        self.save(
            update_fields=["status", "processed_at", "locked_at", "error_message", "updated_at"]
        )

    def mark_failed(self, error: Exception | str, *, max_attempts: int = 5) -> None:
        self.attempts += 1
        self.error_message = str(error)[:2000]
        self.locked_at = None
        if self.attempts >= max_attempts:
            self.status = self.Status.DEAD_LETTER
        else:
            self.status = self.Status.FAILED
            backoff_seconds = min(2**self.attempts, OUTBOX_BACKOFF_CAP_SECONDS)
            self.available_at = timezone.now() + timedelta(seconds=backoff_seconds)
        self.save(
            update_fields=[
                "attempts",
                "error_message",
                "locked_at",
                "status",
                "available_at",
                "updated_at",
            ]
        )

    def safe_payload(self) -> dict[str, Any]:
        return dict(self.payload or {})

    def __str__(self) -> str:
        return f"{self.event_type}:{self.id}"
