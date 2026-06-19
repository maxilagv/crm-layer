"""AI platform persistence models.

Every AI call creates an ``AIRun``; there is no provider call without a record.
``organization_id`` is a UUID (BaseModel convention). API keys are NEVER stored
here: providers read credentials from the environment via settings.
"""

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from crm.core.models import BaseModel

from .domain.enums import (
    AIMessageRole,
    AIProviderType,
    AIPurpose,
    AIRunStatus,
    PromptStatus,
    ToolCallStatus,
)


class AIProvider(BaseModel):
    name = models.CharField(max_length=120)
    provider_type = models.CharField(max_length=32, choices=AIProviderType.choices)
    is_enabled = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "ai_provider"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "provider_type"]),
            models.Index(fields=["organization_id", "is_enabled", "priority"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.provider_type})"


class AIModelConfig(BaseModel):
    provider = models.ForeignKey(AIProvider, on_delete=models.CASCADE, related_name="model_configs")
    purpose = models.CharField(max_length=48, choices=AIPurpose.choices)
    model_name = models.CharField(max_length=120)
    temperature = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.20"),
        validators=[MinValueValidator(0), MaxValueValidator(2)],
    )
    max_tokens = models.PositiveIntegerField(default=1024)
    timeout_seconds = models.PositiveSmallIntegerField(default=60)
    fallback_model = models.CharField(max_length=120, blank=True)
    fallback_provider = models.ForeignKey(
        AIProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fallback_model_configs",
    )
    is_active = models.BooleanField(default=True)
    supports_tools = models.BooleanField(default=False)
    supports_structured_outputs = models.BooleanField(default=False)
    supports_audio = models.BooleanField(default=False)
    supports_images = models.BooleanField(default=False)
    supports_embeddings = models.BooleanField(default=False)

    class Meta:
        db_table = "ai_model_config"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "purpose", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.purpose}:{self.model_name}"


class AIPrompt(BaseModel):
    key = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    purpose = models.CharField(max_length=48, choices=AIPurpose.choices)
    active_version = models.ForeignKey(
        "AIPromptVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_for_prompt",
    )

    class Meta:
        db_table = "ai_prompt"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "key"],
                name="uniq_ai_prompt_org_key",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "purpose"]),
        ]

    def __str__(self) -> str:
        return self.key


class PromptVersionImmutableError(Exception):
    """Raised when content of an ACTIVE prompt version is mutated."""


class AIPromptVersion(BaseModel):
    CONTENT_FIELDS = ("system_prompt", "developer_prompt", "template", "output_schema", "examples")

    prompt = models.ForeignKey(AIPrompt, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16, choices=PromptStatus.choices, default=PromptStatus.DRAFT
    )
    system_prompt = models.TextField(blank=True)
    developer_prompt = models.TextField(blank=True)
    template = models.TextField(blank=True)
    output_schema = models.JSONField(null=True, blank=True)
    examples = models.JSONField(default=list, blank=True)
    change_notes = models.TextField(blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ai_prompt_version"
        constraints = [
            models.UniqueConstraint(
                fields=["prompt", "version"], name="uniq_ai_prompt_version_number"
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["prompt", "status"]),
        ]

    def save(self, *args, **kwargs):
        # An ACTIVE version is immutable: changing a prompt requires a new draft.
        if self.pk is not None:
            original = (
                AIPromptVersion.all_objects.filter(pk=self.pk)
                .values("status", *self.CONTENT_FIELDS)
                .first()
            )
            if original and original["status"] == PromptStatus.ACTIVE:
                changed = [
                    field
                    for field in self.CONTENT_FIELDS
                    if original[field] != getattr(self, field)
                ]
                if changed:
                    raise PromptVersionImmutableError(
                        f"Active prompt version is immutable (fields: {', '.join(changed)}); "
                        "create a new draft instead"
                    )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.prompt_id}:v{self.version} ({self.status})"


class AIRun(BaseModel):
    provider = models.CharField(max_length=32, blank=True)
    model = models.CharField(max_length=120, blank=True)
    purpose = models.CharField(max_length=48, choices=AIPurpose.choices)
    status = models.CharField(
        max_length=24, choices=AIRunStatus.choices, default=AIRunStatus.PENDING
    )
    input_messages = models.JSONField(default=list, blank=True)
    input_context = models.JSONField(default=dict, blank=True)
    output_text = models.TextField(blank=True)
    output_json = models.JSONField(null=True, blank=True)
    # Sanitized provider payload for debugging; never returned by public APIs.
    raw_response = models.JSONField(default=dict, blank=True)
    tool_calls = models.JSONField(default=list, blank=True)
    usage_input_tokens = models.PositiveIntegerField(default=0)
    usage_output_tokens = models.PositiveIntegerField(default=0)
    usage_total_tokens = models.PositiveIntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal("0"))
    latency_ms = models.PositiveIntegerField(default=0)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    prompt_version = models.ForeignKey(
        AIPromptVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name="runs"
    )
    safety_result = models.JSONField(null=True, blank=True)
    # Loose UUID references (modules may not exist yet; no FK coupling).
    conversation_id = models.UUIDField(null=True, blank=True)
    message_id = models.UUIDField(null=True, blank=True)
    contact_id = models.UUIDField(null=True, blank=True)
    lead_id = models.UUIDField(null=True, blank=True)
    client_id = models.UUIDField(null=True, blank=True)
    ticket_id = models.UUIDField(null=True, blank=True)
    task_id = models.UUIDField(null=True, blank=True)
    request_id = models.CharField(max_length=128, blank=True)
    correlation_id = models.CharField(max_length=128, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ai_run"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "purpose", "created_at"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "conversation_id"]),
            models.Index(fields=["organization_id", "provider", "model"]),
            models.Index(fields=["request_id"]),
        ]

    def __str__(self) -> str:
        return f"run:{self.purpose}:{self.status}"


class AIMessage(BaseModel):
    ai_run = models.ForeignKey(AIRun, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=AIMessageRole.choices)
    content = models.TextField(blank=True)
    content_type = models.CharField(max_length=32, default="text")
    token_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "ai_message"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["ai_run", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.role}:{self.ai_run_id}"


class AIToolCall(BaseModel):
    ai_run = models.ForeignKey(AIRun, on_delete=models.CASCADE, related_name="tool_call_records")
    tool_name = models.CharField(max_length=80)
    tool_version = models.CharField(max_length=16, default="1")
    arguments = models.JSONField(default=dict, blank=True)
    validated_arguments = models.JSONField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=ToolCallStatus.choices, default=ToolCallStatus.REQUESTED
    )
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=128, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ai_tool_call"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["ai_run"]),
            models.Index(fields=["organization_id", "tool_name", "status"]),
            models.Index(fields=["organization_id", "idempotency_key"]),
        ]

    def __str__(self) -> str:
        return f"{self.tool_name}:{self.status}"


class AIUsageRecord(BaseModel):
    ai_run = models.ForeignKey(AIRun, on_delete=models.CASCADE, related_name="usage_records")
    provider = models.CharField(max_length=32)
    model = models.CharField(max_length=120)
    purpose = models.CharField(max_length=48, choices=AIPurpose.choices)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cached_tokens = models.PositiveIntegerField(default=0)
    audio_seconds = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    image_count = models.PositiveSmallIntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal("0"))
    currency = models.CharField(max_length=8, default="USD")

    class Meta:
        db_table = "ai_usage_record"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "purpose", "created_at"]),
            models.Index(fields=["organization_id", "provider", "model"]),
        ]

    def __str__(self) -> str:
        return f"usage:{self.purpose}:{self.estimated_cost}"


class AIEmbedding(BaseModel):
    owner_type = models.CharField(max_length=64)
    owner_id = models.UUIDField()
    embedding_model = models.CharField(max_length=120)
    # Stored as a JSON list of floats for maximum compatibility. Next step
    # (documented in README): migrate to pgvector VectorField + ivfflat index
    # once retrieval-by-similarity lands.
    vector = models.JSONField(default=list)
    text_hash = models.CharField(max_length=64)
    source_text = models.TextField(blank=True)

    class Meta:
        db_table = "ai_embedding"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization_id",
                    "owner_type",
                    "owner_id",
                    "embedding_model",
                    "text_hash",
                ],
                name="uniq_ai_embedding_owner_model_hash",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "owner_type", "owner_id"]),
        ]

    def __str__(self) -> str:
        return f"embedding:{self.owner_type}:{self.owner_id}"


class AIEvalCase(BaseModel):
    suite_name = models.CharField(max_length=80)
    case_key = models.CharField(max_length=120)
    purpose = models.CharField(max_length=48, choices=AIPurpose.choices)
    input_payload = models.JSONField(default=dict)
    expected_output = models.JSONField(null=True, blank=True)
    expected_behavior = models.CharField(max_length=64, blank=True)
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ai_eval_case"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "suite_name", "case_key"],
                name="uniq_ai_eval_case_suite_key",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "suite_name", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.suite_name}:{self.case_key}"


class AIEvalResult(BaseModel):
    eval_case = models.ForeignKey(AIEvalCase, on_delete=models.CASCADE, related_name="results")
    prompt_version = models.ForeignKey(
        AIPromptVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eval_results",
    )
    provider = models.CharField(max_length=32, blank=True)
    model = models.CharField(max_length=120, blank=True)
    actual_output = models.JSONField(null=True, blank=True)
    passed = models.BooleanField(default=False)
    score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0"))
    metrics = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "ai_eval_result"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["eval_case", "created_at"]),
            models.Index(fields=["organization_id", "passed"]),
        ]

    def __str__(self) -> str:
        return f"eval:{self.eval_case_id}:{'pass' if self.passed else 'fail'}"
