from django.conf import settings
from django.db import models
from django.utils import timezone

from crm.core.models import BaseModel

from .domain.enums import (
    AutomationActionType,
    AutomationRunStatus,
    AutomationStepStatus,
    AutomationStepType,
    AutomationTriggerType,
)


class AutomationRule(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    trigger_type = models.CharField(max_length=48, choices=AutomationTriggerType.choices)
    conditions = models.JSONField(default=list, blank=True)
    actions = models.JSONField(default=list, blank=True)
    is_enabled = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(default=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="automation_rules",
    )

    class Meta:
        db_table = "automations_rule"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "trigger_type"]),
            models.Index(fields=["organization_id", "is_enabled"]),
            models.Index(fields=["organization_id", "priority"]),
            models.Index(fields=["created_by"]),
        ]

    def __str__(self) -> str:
        return self.name


class AutomationTrigger(BaseModel):
    rule = models.ForeignKey(AutomationRule, on_delete=models.CASCADE, related_name="triggers")
    trigger_type = models.CharField(max_length=48, choices=AutomationTriggerType.choices)
    configuration = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "automations_trigger"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "rule"]),
            models.Index(fields=["organization_id", "trigger_type"]),
        ]

    def __str__(self) -> str:
        return f"trigger:{self.rule_id}:{self.trigger_type}"


class AutomationCondition(BaseModel):
    rule = models.ForeignKey(
        AutomationRule, on_delete=models.CASCADE, related_name="condition_rows"
    )
    order = models.PositiveSmallIntegerField(default=0)
    condition_type = models.CharField(max_length=64, default="field")
    field_path = models.CharField(max_length=255)
    operator = models.CharField(max_length=32, default="eq")
    expected_value = models.JSONField(null=True, blank=True)
    configuration = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "automations_condition"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "rule", "order"]),
        ]

    def __str__(self) -> str:
        return f"condition:{self.rule_id}:{self.field_path}:{self.operator}"


class AutomationAction(BaseModel):
    rule = models.ForeignKey(AutomationRule, on_delete=models.CASCADE, related_name="action_rows")
    order = models.PositiveSmallIntegerField(default=0)
    action_type = models.CharField(max_length=48, choices=AutomationActionType.choices)
    configuration = models.JSONField(default=dict, blank=True)
    required_permission = models.CharField(max_length=120, blank=True)
    timeout_seconds = models.PositiveSmallIntegerField(default=30)

    class Meta:
        db_table = "automations_action"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "rule", "order"]),
            models.Index(fields=["organization_id", "action_type"]),
        ]

    def __str__(self) -> str:
        return f"action:{self.rule_id}:{self.action_type}"


class AutomationRun(BaseModel):
    rule = models.ForeignKey(AutomationRule, on_delete=models.CASCADE, related_name="runs")
    trigger_type = models.CharField(max_length=48, choices=AutomationTriggerType.choices)
    trigger_event_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=32, choices=AutomationRunStatus.choices, default=AutomationRunStatus.RUNNING
    )
    trigger_payload = models.JSONField(default=dict, blank=True)
    reason = models.TextField(blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "automations_run"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "rule", "trigger_event_id"],
                condition=models.Q(trigger_event_id__gt=""),
                name="uniq_automation_run_rule_trigger_event",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "rule"]),
            models.Index(fields=["organization_id", "trigger_type"]),
            models.Index(fields=["organization_id", "status"]),
        ]

    def finish(self, status: str, *, reason: str = "") -> None:
        self.status = status
        if reason:
            self.reason = reason[:2000]
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "reason", "finished_at", "updated_at"])

    def __str__(self) -> str:
        return f"run:{self.rule_id}:{self.status}"


class AutomationRunStep(BaseModel):
    automation_run = models.ForeignKey(
        AutomationRun, on_delete=models.CASCADE, related_name="steps"
    )
    action = models.ForeignKey(
        AutomationAction, on_delete=models.SET_NULL, null=True, blank=True, related_name="run_steps"
    )
    condition = models.ForeignKey(
        AutomationCondition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="run_steps",
    )
    step_type = models.CharField(max_length=16, choices=AutomationStepType.choices)
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16, choices=AutomationStepStatus.choices, default=AutomationStepStatus.PENDING
    )
    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "automations_run_step"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "automation_run"]),
            models.Index(fields=["organization_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"step:{self.automation_run_id}:{self.name}:{self.status}"
