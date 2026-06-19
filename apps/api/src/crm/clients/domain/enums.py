"""Centralized choices for the clients module."""

from django.db import models


class ClientStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    CANCELLED = "cancelled", "Cancelled"
    ONBOARDING = "onboarding", "Onboarding"
    DELINQUENT = "delinquent", "Delinquent"
    ARCHIVED = "archived", "Archived"


class SupportLevel(models.TextChoices):
    STANDARD = "standard", "Standard"
    PRIORITY = "priority", "Priority"
    VIP = "vip", "VIP"
    INTERNAL = "internal", "Internal"


class OnboardingStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not started"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"


class ClientContactRole(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    TECHNICAL = "technical", "Technical"
    BILLING = "billing", "Billing"
    USER = "user", "User"
    OTHER = "other", "Other"


class ServiceType(models.TextChoices):
    CRM = "crm", "CRM"
    AUTOMATION = "automation", "Automation"
    WHATSAPP = "whatsapp", "WhatsApp"
    WEB = "web", "Web"
    INTEGRATION = "integration", "Integration"
    SUPPORT = "support", "Support"
    CONSULTING = "consulting", "Consulting"
    OTHER = "other", "Other"


class ServiceStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"
    PENDING = "pending", "Pending"


class ChangedByType(models.TextChoices):
    USER = "user", "User"
    SYSTEM = "system", "System"
    AUTOMATION = "automation", "Automation"
    WORKER = "worker", "Worker"
    AI_AGENT = "ai_agent", "AI agent"


# Statuses where the client is "active enough" to be routed to support.
SUPPORT_ROUTABLE_STATUSES = (
    ClientStatus.ACTIVE,
    ClientStatus.ONBOARDING,
    ClientStatus.DELINQUENT,
    ClientStatus.PAUSED,
)

# The single status that enforces the unique-active-client-per-contact rule.
UNIQUE_ACTIVE_STATUS = ClientStatus.ACTIVE
