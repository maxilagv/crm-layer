from __future__ import annotations

from crm.audit.domain.enums import SECURITY_SEVERITY_BY_EVENT
from crm.audit.models import AuditSecurityEvent

from .audit_sanitizer import sanitize_payload
from .context import (
    actor_id_for,
    actor_type_for,
    client_ip,
    organization_id_for,
    request_ids,
    request_user_agent,
)


class SecurityEventLogger:
    @staticmethod
    def log(
        *,
        event_type: str,
        actor=None,
        organization=None,
        request=None,
        severity: str | None = None,
        description: str = "",
        metadata: dict | None = None,
    ) -> AuditSecurityEvent:
        request_id, correlation_id = request_ids(request)
        return AuditSecurityEvent.objects.create(
            organization_id=organization_id_for(organization),
            event_type=event_type,
            severity=severity or SECURITY_SEVERITY_BY_EVENT.get(event_type, "medium"),
            actor_type=actor_type_for(actor),
            actor_id=actor_id_for(actor),
            ip_address=client_ip(request),
            user_agent=request_user_agent(request),
            request_id=request_id,
            correlation_id=correlation_id,
            description=description[:2000],
            metadata=sanitize_payload(metadata or {}),
        )
