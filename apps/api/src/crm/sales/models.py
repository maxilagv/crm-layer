from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from crm.contacts.models import Contact
from crm.conversations.models import Conversation, Message
from crm.core.models import BaseModel

from .domain.enums import (
    CallRequestStatus,
    FollowupStatus,
    ObjectionType,
    OpportunityStage,
    PlaybookStatus,
)

OPEN_CALL_REQUEST_STATUSES = (
    CallRequestStatus.REQUESTED,
    CallRequestStatus.OWNER_NOTIFIED,
    CallRequestStatus.SCHEDULED,
)


class SalesOpportunity(BaseModel):
    lead = models.ForeignKey("leads.Lead", on_delete=models.CASCADE, related_name="opportunities")
    contact = models.ForeignKey(
        Contact, on_delete=models.PROTECT, related_name="sales_opportunities"
    )
    title = models.CharField(max_length=255)
    value_estimate_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    value_estimate_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="USD")
    stage = models.CharField(
        max_length=32, choices=OpportunityStage.choices, default=OpportunityStage.NEW
    )
    probability = models.PositiveSmallIntegerField(
        default=10, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    expected_close_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "sales_opportunity"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(probability__gte=0, probability__lte=100),
                name="ck_sales_opportunity_probability_0_100",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(value_estimate_min__isnull=True)
                    | models.Q(value_estimate_max__isnull=True)
                    | models.Q(value_estimate_min__lte=models.F("value_estimate_max"))
                ),
                name="ck_sales_opportunity_value_range",
            ),
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "stage"]),
            models.Index(fields=["organization_id", "probability"]),
            models.Index(fields=["organization_id", "expected_close_date"]),
            models.Index(fields=["organization_id", "lead"]),
        ]

    def __str__(self) -> str:
        return self.title


class SalesFollowup(BaseModel):
    lead = models.ForeignKey("leads.Lead", on_delete=models.CASCADE, related_name="sales_followups")
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="sales_followups")
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_followups",
    )
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=32, choices=FollowupStatus.choices, default=FollowupStatus.PENDING
    )
    due_at = models.DateTimeField(db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "sales_followup"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "idempotency_key"],
                condition=models.Q(idempotency_key__gt=""),
                name="uniq_sales_followup_org_idempotency_key",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "lead"]),
            models.Index(fields=["organization_id", "status", "due_at"]),
            models.Index(fields=["organization_id", "contact"]),
        ]

    def __str__(self) -> str:
        return self.title


class SalesObjection(BaseModel):
    lead = models.ForeignKey("leads.Lead", on_delete=models.CASCADE, related_name="objections")
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="sales_objections")
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_objections",
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_objections",
    )
    objection_type = models.CharField(
        max_length=32, choices=ObjectionType.choices, default=ObjectionType.OTHER
    )
    summary = models.TextField(blank=True)
    raw_text = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        db_table = "sales_objection"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "lead", "objection_type", "message"],
                condition=models.Q(message__isnull=False),
                name="uniq_sales_objection_org_lead_type_message",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "lead"]),
            models.Index(fields=["organization_id", "objection_type"]),
            models.Index(fields=["organization_id", "message"]),
        ]

    def __str__(self) -> str:
        return f"objection:{self.lead_id}:{self.objection_type}"


class SalesPlaybook(BaseModel):
    key = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=PlaybookStatus.choices, default=PlaybookStatus.ACTIVE
    )
    trigger_intents = models.JSONField(default=list, blank=True)
    content = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "sales_playbook"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "key"],
                name="uniq_sales_playbook_org_key",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "key"]),
        ]

    def __str__(self) -> str:
        return self.key


class SalesCallRequest(BaseModel):
    lead = models.ForeignKey("leads.Lead", on_delete=models.CASCADE, related_name="call_requests")
    contact = models.ForeignKey(
        Contact, on_delete=models.PROTECT, related_name="sales_call_requests"
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_call_requests",
    )
    status = models.CharField(
        max_length=32, choices=CallRequestStatus.choices, default=CallRequestStatus.REQUESTED
    )
    requested_at = models.DateTimeField(default=timezone.now, db_index=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    owner_notified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "sales_call_request"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "lead"],
                condition=models.Q(status__in=OPEN_CALL_REQUEST_STATUSES),
                name="uniq_open_call_request_org_lead",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "lead"]),
            models.Index(fields=["organization_id", "contact"]),
            models.Index(fields=["organization_id", "scheduled_at"]),
        ]

    def mark_owner_notified(self) -> None:
        self.status = CallRequestStatus.OWNER_NOTIFIED
        self.owner_notified_at = timezone.now()
        self.save(update_fields=["status", "owner_notified_at", "updated_at"])

    def mark_scheduled(self, scheduled_at, *, notes: str = "") -> None:
        self.status = CallRequestStatus.SCHEDULED
        self.scheduled_at = scheduled_at
        if notes:
            self.notes = notes
        self.save(update_fields=["status", "scheduled_at", "notes", "updated_at"])

    def __str__(self) -> str:
        return f"call-request:{self.lead_id}:{self.status}"


ZERO_DECIMAL = Decimal("0.00")
