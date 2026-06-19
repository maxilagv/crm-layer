import hashlib
import secrets
from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from crm.core.models import BaseModel
from crm.core.security.permissions import ALL_PERMISSIONS

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="America/Argentina/Buenos_Aires")
    locale = models.CharField(max_length=16, default="es")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "accounts_user"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["email"]),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = User.objects.normalize_email(self.email)
        super().save(*args, **kwargs)

    def mark_logged_in(self) -> None:
        self.last_login = timezone.now()
        self.last_login_at = timezone.now()
        self.save(update_fields=["last_login", "last_login_at", "updated_at"])

    def __str__(self) -> str:
        return self.email


@dataclass(frozen=True)
class GeneratedAPIKey:
    raw_key: str
    prefix: str
    hashed_key: str


class APIKey(BaseModel):
    name = models.CharField(max_length=120)
    prefix = models.CharField(max_length=16, db_index=True)
    hashed_key = models.CharField(max_length=128)
    scopes = models.JSONField(default=list, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "accounts_api_key"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "prefix"]),
            models.Index(fields=["revoked_at", "expires_at"]),
        ]

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def generate(cls) -> GeneratedAPIKey:
        secret = secrets.token_urlsafe(32)
        prefix = secrets.token_hex(4)
        raw_key = f"acrm_{prefix}_{secret}"
        return GeneratedAPIKey(
            raw_key=raw_key,
            prefix=prefix,
            hashed_key=cls.hash_key(raw_key),
        )

    def is_active_key(self) -> bool:
        if self.revoked_at is not None:
            return False
        return self.expires_at is None or self.expires_at > timezone.now()

    def has_scope(self, scope: str) -> bool:
        return scope in set(self.scopes or [])

    def permission_scopes(self) -> set[str]:
        return set(self.scopes or []) & set(ALL_PERMISSIONS)

    def mark_used(self) -> None:
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at", "updated_at"])

    def revoke(self) -> None:
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at", "updated_at"])

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix})"
