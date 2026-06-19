from __future__ import annotations

from typing import Any

from crm.audit.domain.enums import AUDIT_ACTION_ALIASES
from crm.audit.models import AuditEvent, AuditLog

from .audit_sanitizer import sanitize_payload
from .context import (
    actor_id_for,
    actor_type_for,
    client_ip,
    organization_id_for,
    request_ids,
    request_user_agent,
)


class AuditLogger:
    @staticmethod
    def log(
        *,
        action: str,
        actor=None,
        actor_type: str | None = None,
        organization=None,
        request=None,
        resource_type: str = "",
        resource_id: str = "",
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        request_id, correlation_id = request_ids(request)
        return AuditLog.objects.create(
            organization_id=organization_id_for(organization),
            actor_type=actor_type or actor_type_for(actor),
            actor_id=actor_id_for(actor),
            action=AUDIT_ACTION_ALIASES.get(action, action),
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else "",
            before=sanitize_payload(before or {}),
            after=sanitize_payload(after or {}),
            ip_address=client_ip(request),
            user_agent=request_user_agent(request),
            request_id=request_id,
            correlation_id=correlation_id,
            metadata=sanitize_payload(metadata or {}),
        )


def audit_event_create(
    *,
    event_type: str,
    actor=None,
    organization=None,
    request=None,
    resource_type: str = "",
    resource_id: str = "",
    changes: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Compatibility entry point used by previous phases.

    It preserves the legacy AuditEvent row and mirrors the event into the
    append-only AuditLog introduced in Fase 9.
    """
    request_id, correlation_id = request_ids(request)
    clean_changes = sanitize_payload(changes or {})
    clean_metadata = sanitize_payload(metadata or {})
    organization_id = organization_id_for(organization)

    event = AuditEvent.objects.create(
        organization_id=organization_id,
        actor_type=actor_type_for(actor),
        actor_id=actor_id_for(actor),
        event_type=event_type,
        action=event_type,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else "",
        ip_address=client_ip(request),
        user_agent=request_user_agent(request),
        request_id=request_id,
        changes=clean_changes,
        before=clean_changes.get("before", {}),
        after=clean_changes.get("after", {}),
        metadata=(
            {**clean_metadata, "correlation_id": correlation_id}
            if correlation_id
            else clean_metadata
        ),
    )
    before, after = _before_after_from_changes(clean_changes)
    AuditLogger.log(
        action=event_type,
        actor=actor,
        organization=organization,
        request=request,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else "",
        before=before,
        after=after,
        metadata=clean_metadata,
    )
    if event_type in {"permission_denied", "login_failed", "login_succeeded", "login_success"}:
        from .security_event_logger import SecurityEventLogger

        SecurityEventLogger.log(
            event_type=event_type,
            actor=actor,
            organization=organization,
            request=request,
            description=(
                clean_metadata.get("reason", "") if isinstance(clean_metadata, dict) else ""
            ),
            metadata=clean_metadata,
        )
    return event


def _before_after_from_changes(changes: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    for key, value in changes.items():
        if not isinstance(value, dict):
            continue
        if "from" in value or "before" in value:
            before[key] = value.get("from", value.get("before"))
        if "to" in value or "after" in value:
            after[key] = value.get("to", value.get("after"))
    if not before and isinstance(changes.get("before"), dict):
        before = changes["before"]
    if not after and isinstance(changes.get("after"), dict):
        after = changes["after"]
    return before, after
