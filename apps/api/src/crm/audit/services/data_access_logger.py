from __future__ import annotations

from crm.audit.models import AuditDataAccessLog

from .audit_sanitizer import sanitize_payload
from .context import (
    actor_id_for,
    actor_type_for,
    client_ip,
    organization_id_for,
    request_ids,
    request_user_agent,
)


class DataAccessLogger:
    @staticmethod
    def log(
        *,
        organization,
        resource_type: str,
        access_type: str,
        actor=None,
        request=None,
        resource_id: str = "",
        field_names: list[str] | None = None,
        reason: str = "",
        metadata: dict | None = None,
    ) -> AuditDataAccessLog:
        request_id, correlation_id = request_ids(request)
        return AuditDataAccessLog.objects.create(
            organization_id=organization_id_for(organization),
            actor_type=actor_type_for(actor),
            actor_id=actor_id_for(actor),
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else "",
            access_type=access_type,
            field_names=sanitize_payload(field_names or []),
            reason=reason[:255],
            request_id=request_id,
            correlation_id=correlation_id,
            ip_address=client_ip(request),
            user_agent=request_user_agent(request),
            metadata=sanitize_payload(metadata or {}),
        )
