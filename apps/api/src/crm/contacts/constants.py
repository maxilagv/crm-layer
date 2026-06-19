"""Centralized choices and event names for the contacts module."""

from django.db import models


class ContactType(models.TextChoices):
    """Classification of a contact (not a conversation state)."""

    UNKNOWN = "unknown", "Unknown"
    LEAD = "lead", "Lead"
    CLIENT = "client", "Client"
    INTERNAL = "internal", "Internal"
    SUPPLIER = "supplier", "Supplier"
    BLOCKED = "blocked", "Blocked"


class ContactStatus(models.TextChoices):
    """Availability/lifecycle state of a contact."""

    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    BLOCKED = "blocked", "Blocked"
    ARCHIVED = "archived", "Archived"


class ContactSource(models.TextChoices):
    """Where the contact originated."""

    UNKNOWN = "unknown", "Unknown"
    MANUAL = "manual", "Manual"
    WHATSAPP = "whatsapp", "WhatsApp"
    EMAIL = "email", "Email"
    IMPORT = "import", "Import"
    API = "api", "API"
    SYSTEM = "system", "System"
    PROSPECTING = "prospecting", "Prospecting"


class NoteVisibility(models.TextChoices):
    INTERNAL = "internal", "Internal"
    TEAM = "team", "Team"
    PRIVATE = "private", "Private"


# Versioned internal event types (emitted via the outbox).
EVENT_CONTACT_CREATED = "contact.created.v1"
EVENT_CONTACT_UPDATED = "contact.updated.v1"
