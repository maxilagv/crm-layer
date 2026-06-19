from django.db import models
from django.utils import timezone

from crm.contacts.models import Contact
from crm.conversations.models import Conversation, Message
from crm.core.models import BaseModel

from .domain.enums import (
    AuthoritySignal,
    BudgetSignal,
    LeadSourceType,
    LeadStage,
    LeadStatus,
    LeadTemperature,
    LeadUrgency,
    StageChangedByType,
)


class Lead(BaseModel):
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="leads")
    status = models.CharField(max_length=32, choices=LeadStatus.choices, default=LeadStatus.ACTIVE)
    stage = models.CharField(max_length=32, choices=LeadStage.choices, default=LeadStage.NEW)
    score = models.PositiveSmallIntegerField(default=0)
    temperature = models.CharField(
        max_length=16, choices=LeadTemperature.choices, default=LeadTemperature.COLD
    )
    service_interest = models.CharField(max_length=255, blank=True)
    budget_signal = models.CharField(
        max_length=16, choices=BudgetSignal.choices, default=BudgetSignal.UNKNOWN
    )
    urgency = models.CharField(
        max_length=16, choices=LeadUrgency.choices, default=LeadUrgency.UNKNOWN
    )
    authority_signal = models.CharField(
        max_length=32, choices=AuthoritySignal.choices, default=AuthoritySignal.UNKNOWN
    )
    pain_points = models.JSONField(default=list, blank=True)
    technical_needs = models.JSONField(default=list, blank=True)
    business_needs = models.JSONField(default=list, blank=True)
    next_best_action = models.CharField(max_length=255, blank=True)
    last_scored_at = models.DateTimeField(null=True, blank=True, db_index=True)
    summary = models.TextField(blank=True)

    class Meta:
        db_table = "leads_lead"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "contact"],
                condition=models.Q(status=LeadStatus.ACTIVE),
                name="uniq_active_lead_org_contact",
            ),
            models.CheckConstraint(
                condition=models.Q(score__gte=0, score__lte=100),
                name="ck_lead_score_0_100",
            ),
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "stage"]),
            models.Index(fields=["organization_id", "temperature"]),
            models.Index(fields=["organization_id", "score"]),
            models.Index(fields=["organization_id", "contact"]),
            models.Index(fields=["organization_id", "last_scored_at"]),
        ]

    def __str__(self) -> str:
        return f"lead:{self.contact_id}:{self.stage}:{self.score}"


class LeadScoreSnapshot(BaseModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="score_snapshots")
    score = models.PositiveSmallIntegerField()
    temperature = models.CharField(max_length=16, choices=LeadTemperature.choices)
    reasoning_summary = models.TextField(blank=True)
    factors = models.JSONField(default=dict)
    ai_run_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "leads_lead_score_snapshot"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(score__gte=0, score__lte=100),
                name="ck_lead_snapshot_score_0_100",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "lead", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"lead-score:{self.lead_id}:{self.score}"


class LeadStageHistory(BaseModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="stage_history")
    from_stage = models.CharField(max_length=32, blank=True)
    to_stage = models.CharField(max_length=32, choices=LeadStage.choices)
    reason = models.TextField(blank=True)
    changed_by_id = models.UUIDField(null=True, blank=True)
    changed_by_type = models.CharField(
        max_length=32, choices=StageChangedByType.choices, default=StageChangedByType.SYSTEM
    )
    ai_run_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "leads_lead_stage_history"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "lead", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"lead-stage:{self.lead_id}:{self.from_stage}->{self.to_stage}"


class LeadSource(BaseModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="sources")
    source_type = models.CharField(
        max_length=32, choices=LeadSourceType.choices, default=LeadSourceType.UNKNOWN
    )
    source_detail = models.CharField(max_length=255, blank=True)
    campaign = models.CharField(max_length=255, blank=True)
    channel = models.CharField(max_length=32, blank=True)
    first_touch_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_sources",
    )
    first_touch_conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_sources",
    )
    first_touch_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "leads_lead_source"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "lead"]),
            models.Index(fields=["organization_id", "source_type"]),
        ]

    def __str__(self) -> str:
        return f"lead-source:{self.lead_id}:{self.source_type}"
