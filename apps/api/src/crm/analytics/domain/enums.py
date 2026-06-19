from django.db import models


class AnalyticsEventSource(models.TextChoices):
    API = "api", "API"
    WORKER = "worker", "Worker"
    WEBHOOK = "webhook", "Webhook"
    SYSTEM = "system", "System"
    AI = "ai", "AI"


class AlertSeverity(models.TextChoices):
    INFO = "info", "Info"
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class AlertStatus(models.TextChoices):
    OPEN = "open", "Open"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    RESOLVED = "resolved", "Resolved"
    SUPPRESSED = "suppressed", "Suppressed"


class ThresholdOperator(models.TextChoices):
    GT = "gt", "Greater than"
    GTE = "gte", "Greater than or equal"
    LT = "lt", "Less than"
    LTE = "lte", "Less than or equal"
    EQ = "eq", "Equal"
