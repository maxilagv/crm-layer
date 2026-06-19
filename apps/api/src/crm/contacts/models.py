"""Contacts domain models.

All models inherit :class:`crm.core.models.BaseModel` (UUID pk, ``organization_id``
UUID, timestamps, soft delete, ``metadata``). ``organization_id`` is denormalized
onto every child row so tenant-scoped queries never need to join through the parent.
"""

from django.conf import settings
from django.db import models

from crm.core.models import BaseModel

from .constants import (
    ContactSource,
    ContactStatus,
    ContactType,
    NoteVisibility,
)


class Contact(BaseModel):
    display_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    source = models.CharField(
        max_length=32, choices=ContactSource.choices, default=ContactSource.UNKNOWN
    )
    type = models.CharField(
        max_length=32, choices=ContactType.choices, default=ContactType.UNKNOWN, db_index=True
    )
    status = models.CharField(
        max_length=32, choices=ContactStatus.choices, default=ContactStatus.ACTIVE
    )
    language = models.CharField(max_length=16, default="es")
    timezone = models.CharField(max_length=64, default="America/Argentina/Buenos_Aires")
    avatar_url = models.URLField(max_length=1024, blank=True)
    summary = models.TextField(blank=True)

    class Meta:
        db_table = "contacts_contact"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "display_name"]),
            models.Index(fields=["organization_id", "type", "status"]),
            models.Index(fields=["organization_id", "updated_at"]),
        ]

    def __str__(self) -> str:
        return self.display_name


class ContactPhone(BaseModel):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="phones")
    phone_e164 = models.CharField(max_length=20)
    country_code = models.CharField(max_length=8, blank=True)
    is_primary = models.BooleanField(default=False)
    is_whatsapp = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "contacts_contact_phone"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "phone_e164"],
                name="uniq_contact_phone_org_e164",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "phone_e164"]),
            models.Index(fields=["contact", "is_primary"]),
        ]

    def __str__(self) -> str:
        return self.phone_e164


class ContactEmail(BaseModel):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="emails")
    email = models.EmailField(max_length=254)
    normalized_email = models.CharField(max_length=254)
    is_primary = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "contacts_contact_email"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "normalized_email"],
                name="uniq_contact_email_org_normalized",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "normalized_email"]),
            models.Index(fields=["contact", "is_primary"]),
        ]

    def __str__(self) -> str:
        return self.email


class Company(BaseModel):
    name = models.CharField(max_length=255)
    website = models.URLField(max_length=1024, blank=True)
    industry = models.CharField(max_length=120, blank=True)
    size = models.CharField(max_length=64, blank=True)
    country = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "contacts_company"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "name"]),
        ]

    def __str__(self) -> str:
        return self.name


class ContactCompany(BaseModel):
    """Explicit many-to-many link between a contact and a company (B2B-ready)."""

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="company_links")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="contact_links")
    role = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=120, blank=True)
    is_primary = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "contacts_contact_company"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "contact", "company"],
                name="uniq_contact_company_org_contact_company",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["contact", "is_primary"]),
            models.Index(fields=["company"]),
        ]

    def __str__(self) -> str:
        return f"{self.contact_id}:{self.company_id}"


class ContactTag(BaseModel):
    """A tag assignment on a contact (slug is unique per contact)."""

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=80)
    color = models.CharField(max_length=16, blank=True)

    class Meta:
        db_table = "contacts_contact_tag"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "contact", "slug"],
                name="uniq_contact_tag_org_contact_slug",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "slug"]),
            models.Index(fields=["contact"]),
        ]

    def __str__(self) -> str:
        return self.name


class ContactNote(BaseModel):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_notes",
    )
    body = models.TextField()
    visibility = models.CharField(
        max_length=16, choices=NoteVisibility.choices, default=NoteVisibility.INTERNAL
    )

    class Meta:
        db_table = "contacts_contact_note"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["contact", "created_at"]),
            models.Index(fields=["organization_id", "visibility"]),
        ]

    def __str__(self) -> str:
        return f"note:{self.contact_id}"


class ContactEvent(BaseModel):
    """Append-only operational history of a contact (distinct from the outbox)."""

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "contacts_contact_event"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["contact", "occurred_at"]),
            models.Index(fields=["organization_id", "event_type"]),
        ]

    def __str__(self) -> str:
        return self.event_type
