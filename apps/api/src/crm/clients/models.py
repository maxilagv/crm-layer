"""Clients domain models.

A Client is the support-mode counterpart of a lead: it always wraps a
``contacts.Contact`` (whose ``type`` is ``client``). At most one ACTIVE client
may exist per contact within an organization (enforced by a partial unique
constraint). Every status change is recorded in ``ClientStatusHistory``.
"""

from django.db import models

from crm.contacts.models import Company, Contact
from crm.core.models import BaseModel

from .domain.enums import (
    UNIQUE_ACTIVE_STATUS,
    ChangedByType,
    ClientContactRole,
    ClientStatus,
    OnboardingStatus,
    ServiceStatus,
    ServiceType,
    SupportLevel,
)


class Client(BaseModel):
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="clients")
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="clients"
    )
    display_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16, choices=ClientStatus.choices, default=ClientStatus.ACTIVE
    )
    service_plan = models.CharField(max_length=120, blank=True)
    support_level = models.CharField(
        max_length=16, choices=SupportLevel.choices, default=SupportLevel.STANDARD
    )
    onboarding_status = models.CharField(
        max_length=16, choices=OnboardingStatus.choices, default=OnboardingStatus.NOT_STARTED
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "clients_client"
        constraints = [
            # At most one ACTIVE client per contact per organization.
            models.UniqueConstraint(
                fields=["organization_id", "contact"],
                condition=models.Q(status=UNIQUE_ACTIVE_STATUS.value, deleted_at__isnull=True),
                name="uniq_active_client_per_contact",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "support_level"]),
            models.Index(fields=["organization_id", "contact"]),
        ]

    def __str__(self) -> str:
        return self.display_name


class ClientContact(BaseModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="client_contacts")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="client_links")
    role = models.CharField(
        max_length=16, choices=ClientContactRole.choices, default=ClientContactRole.USER
    )
    is_primary = models.BooleanField(default=False)
    can_request_support = models.BooleanField(default=True)
    receives_notifications = models.BooleanField(default=False)

    class Meta:
        db_table = "clients_client_contact"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "client", "contact"],
                name="uniq_client_contact_org_client_contact",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "client"]),
            models.Index(fields=["organization_id", "contact"]),
            models.Index(fields=["organization_id", "can_request_support"]),
        ]

    def __str__(self) -> str:
        return f"{self.client_id}:{self.contact_id}:{self.role}"


class ClientService(BaseModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=255)
    service_type = models.CharField(
        max_length=16, choices=ServiceType.choices, default=ServiceType.OTHER
    )
    status = models.CharField(
        max_length=16, choices=ServiceStatus.choices, default=ServiceStatus.ACTIVE
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    configuration = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "clients_client_service"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "client"]),
            models.Index(fields=["organization_id", "service_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.service_type})"


class ClientStatusHistory(BaseModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16)
    reason = models.CharField(max_length=255, blank=True)
    changed_by_id = models.UUIDField(null=True, blank=True)
    changed_by_type = models.CharField(
        max_length=16, choices=ChangedByType.choices, default=ChangedByType.SYSTEM
    )

    class Meta:
        db_table = "clients_client_status_history"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["client", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.client_id}:{self.from_status}->{self.to_status}"
