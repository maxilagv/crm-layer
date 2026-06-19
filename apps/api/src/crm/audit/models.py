from django.db import models

from crm.core.models import BaseModel


class AuditActorType(models.TextChoices):
    USER = "user", "User"
    AI_AGENT = "ai_agent", "AI agent"
    SYSTEM = "system", "System"
    WEBHOOK = "webhook", "Webhook"
    WORKER = "worker", "Worker"
    API_KEY = "api_key", "API key"


class AuditSeverity(models.TextChoices):
    INFO = "info", "Info"
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class AuditAccessType(models.TextChoices):
    VIEW = "view", "View"
    LIST = "list", "List"
    EXPORT = "export", "Export"
    DOWNLOAD = "download", "Download"
    SEARCH = "search", "Search"
    SIGNED_URL = "signed_url", "Signed URL"
    ADMIN_VIEW = "admin_view", "Admin view"


class AuditAIDecisionType(models.TextChoices):
    SALES_REPLY = "sales_reply", "Sales reply"
    SUPPORT_REPLY = "support_reply", "Support reply"
    LEAD_SCORING = "lead_scoring", "Lead scoring"
    TASK_EXTRACTION = "task_extraction", "Task extraction"
    AUDIO_TICKET_EXTRACTION = "audio_ticket_extraction", "Audio ticket extraction"
    RISK_CLASSIFICATION = "risk_classification", "Risk classification"
    CONVERSATION_SUMMARY = "conversation_summary", "Conversation summary"
    IMAGE_GENERATION = "image_generation", "Image generation"
    TOOL_CALL = "tool_call", "Tool call"
    SAFETY_GUARD = "safety_guard", "Safety guard"


class AuditEvent(BaseModel):
    actor_type = models.CharField(max_length=64, blank=True)
    actor_id = models.UUIDField(null=True, blank=True)
    event_type = models.CharField(max_length=120, blank=True)
    action = models.CharField(max_length=120)
    resource_type = models.CharField(max_length=120, blank=True)
    resource_id = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=128, blank=True)

    class Meta:
        db_table = "audit_audit_event"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "event_type"]),
            models.Index(fields=["organization_id", "action"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return self.event_type or self.action


class AuditLog(BaseModel):
    actor_type = models.CharField(max_length=32, choices=AuditActorType.choices)
    actor_id = models.UUIDField(null=True, blank=True)
    action = models.CharField(max_length=120)
    resource_type = models.CharField(max_length=120, blank=True)
    resource_id = models.CharField(max_length=120, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    request_id = models.CharField(max_length=128, blank=True)
    correlation_id = models.CharField(max_length=128, blank=True)

    class Meta:
        db_table = "audit_log"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "action", "created_at"]),
            models.Index(fields=["organization_id", "actor_type", "created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["request_id"]),
            models.Index(fields=["correlation_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action}:{self.resource_type}:{self.resource_id}"


class AuditDataAccessLog(BaseModel):
    actor_type = models.CharField(max_length=32, choices=AuditActorType.choices)
    actor_id = models.UUIDField(null=True, blank=True)
    resource_type = models.CharField(max_length=120)
    resource_id = models.CharField(max_length=120, blank=True)
    access_type = models.CharField(max_length=32, choices=AuditAccessType.choices)
    field_names = models.JSONField(default=list, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    request_id = models.CharField(max_length=128, blank=True)
    correlation_id = models.CharField(max_length=128, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "audit_data_access_log"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "resource_type", "created_at"]),
            models.Index(fields=["organization_id", "access_type", "created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["request_id"]),
            models.Index(fields=["correlation_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.access_type}:{self.resource_type}:{self.resource_id}"


class AuditSecurityEvent(BaseModel):
    event_type = models.CharField(max_length=120)
    severity = models.CharField(max_length=16, choices=AuditSeverity.choices)
    actor_type = models.CharField(max_length=32, choices=AuditActorType.choices)
    actor_id = models.UUIDField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    request_id = models.CharField(max_length=128, blank=True)
    correlation_id = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "audit_security_event"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "event_type", "created_at"]),
            models.Index(fields=["organization_id", "severity", "created_at"]),
            models.Index(fields=["request_id"]),
            models.Index(fields=["correlation_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.severity}"


class AuditAIDecision(BaseModel):
    ai_run_id = models.UUIDField(null=True, blank=True, db_index=True)
    purpose = models.CharField(max_length=64, blank=True)
    provider = models.CharField(max_length=64, blank=True)
    model = models.CharField(max_length=120, blank=True)
    prompt_version_id = models.UUIDField(null=True, blank=True)
    decision_type = models.CharField(max_length=64, choices=AuditAIDecisionType.choices)
    decision = models.JSONField(default=dict, blank=True)
    risk_level = models.CharField(max_length=32, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    input_summary = models.TextField(blank=True)
    output_summary = models.TextField(blank=True)
    safety_decision = models.CharField(max_length=64, blank=True)
    tool_calls_count = models.PositiveIntegerField(default=0)
    blocked_reason = models.CharField(max_length=255, blank=True)
    resource_type = models.CharField(max_length=120, blank=True)
    resource_id = models.UUIDField(null=True, blank=True)
    conversation_id = models.UUIDField(null=True, blank=True)
    contact_id = models.UUIDField(null=True, blank=True)
    lead_id = models.UUIDField(null=True, blank=True)
    ticket_id = models.UUIDField(null=True, blank=True)
    task_id = models.UUIDField(null=True, blank=True)
    request_id = models.CharField(max_length=128, blank=True)
    correlation_id = models.CharField(max_length=128, blank=True)

    class Meta:
        db_table = "audit_ai_decision"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "decision_type", "created_at"]),
            models.Index(fields=["organization_id", "purpose", "created_at"]),
            models.Index(fields=["organization_id", "provider", "model"]),
            models.Index(fields=["organization_id", "conversation_id"]),
            models.Index(fields=["organization_id", "lead_id"]),
            models.Index(fields=["organization_id", "ticket_id"]),
            models.Index(fields=["request_id"]),
            models.Index(fields=["correlation_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.decision_type}:{self.ai_run_id}"


class AuditExternalRequest(BaseModel):
    provider = models.CharField(max_length=64)
    service = models.CharField(max_length=64, blank=True)
    operation = models.CharField(max_length=120, blank=True)
    method = models.CharField(max_length=12, blank=True)
    url_host = models.CharField(max_length=255, blank=True)
    url_path = models.CharField(max_length=512, blank=True)
    url_hash = models.CharField(max_length=64, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)
    error_code = models.CharField(max_length=120, blank=True)
    error_message = models.TextField(blank=True)
    request_id = models.CharField(max_length=128, blank=True)
    correlation_id = models.CharField(max_length=128, blank=True)
    resource_type = models.CharField(max_length=120, blank=True)
    resource_id = models.CharField(max_length=120, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)
    request_metadata = models.JSONField(default=dict, blank=True)
    response_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "audit_external_request"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "provider", "created_at"]),
            models.Index(fields=["organization_id", "success", "created_at"]),
            models.Index(fields=["organization_id", "error_code", "created_at"]),
            models.Index(fields=["request_id"]),
            models.Index(fields=["correlation_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.operation}:{self.status_code or 'error'}"
