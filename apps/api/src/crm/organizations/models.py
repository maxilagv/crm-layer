import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from crm.core.models import BaseModel, SoftDeleteManager
from crm.core.security.permissions import Role


class Organization(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        ARCHIVED = "archived", "Archived"

    class Plan(models.TextChoices):
        PRIVATE = "private", "Private"
        STARTER = "starter", "Starter"
        PRO = "pro", "Pro"
        ENTERPRISE = "enterprise", "Enterprise"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=120, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_organizations",
    )
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE)
    plan = models.CharField(max_length=32, choices=Plan.choices, default=Plan.PRIVATE)
    default_timezone = models.CharField(max_length=64, default="America/Argentina/Buenos_Aires")
    default_language = models.CharField(max_length=16, default="es")

    class Meta:
        db_table = "organizations_organization"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INVITED = "invited", "Invited"
        SUSPENDED = "suspended", "Suspended"
        REMOVED = "removed", "Removed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=32,
        choices=[(role.value, role.value) for role in Role],
        default=Role.VIEWER.value,
    )
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "organizations_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="uniq_membership_organization_user",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.organization_id}:{self.role}"

    def soft_delete(self, *, save: bool = True) -> None:
        self.deleted_at = timezone.now()
        if save:
            self.save(update_fields=["deleted_at", "updated_at"])
