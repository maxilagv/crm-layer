import secrets
from collections.abc import Iterable
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from crm.accounts.models import APIKey
from crm.audit.services import audit_event_create
from crm.core.security.permissions import ALL_PERMISSIONS


@dataclass(frozen=True)
class CreatedAPIKey:
    record: APIKey
    raw_key: str


def validate_scopes(scopes: Iterable[str]) -> list[str]:
    clean = sorted(set(scopes or []))
    invalid = [scope for scope in clean if scope not in ALL_PERMISSIONS]
    if invalid:
        raise ValidationError({"scopes": [f"Invalid scopes: {', '.join(invalid)}"]})
    return clean


@transaction.atomic
def create_api_key(
    *,
    organization,
    name: str,
    scopes: Iterable[str],
    created_by,
    expires_at=None,
    request=None,
) -> CreatedAPIKey:
    generated = APIKey.generate()
    record = APIKey.objects.create(
        organization_id=organization.id,
        name=name,
        prefix=generated.prefix,
        hashed_key=generated.hashed_key,
        scopes=validate_scopes(scopes),
        expires_at=expires_at,
        created_by_id=getattr(created_by, "id", None),
    )
    audit_event_create(
        event_type="api_key_created",
        actor=created_by,
        organization=organization,
        request=request,
        resource_type="accounts_api_key",
        resource_id=str(record.id),
        changes={"name": name, "scopes": record.scopes, "expires_at": str(expires_at or "")},
    )
    return CreatedAPIKey(record=record, raw_key=generated.raw_key)


@transaction.atomic
def revoke_api_key(*, api_key: APIKey, actor, organization, request=None) -> APIKey:
    api_key.revoked_at = timezone.now()
    api_key.save(update_fields=["revoked_at", "updated_at"])
    audit_event_create(
        event_type="api_key_revoked",
        actor=actor,
        organization=organization,
        request=request,
        resource_type="accounts_api_key",
        resource_id=str(api_key.id),
    )
    return api_key


def verify_api_key(raw_key: str) -> APIKey | None:
    try:
        marker, prefix, _secret = raw_key.split("_", 2)
    except ValueError:
        return None
    if marker != "acrm":
        return None

    candidates = APIKey.objects.filter(prefix=prefix, revoked_at__isnull=True)
    raw_hash = APIKey.hash_key(raw_key)
    for candidate in candidates:
        if candidate.is_active_key() and secrets.compare_digest(candidate.hashed_key, raw_hash):
            candidate.mark_used()
            return candidate
    return None
