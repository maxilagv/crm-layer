from __future__ import annotations

from crm.audit.models import AuditExternalRequest

from .audit_sanitizer import sanitize_error_message, sanitize_payload, sanitize_url
from .context import organization_id_for, request_ids


class ExternalRequestLogger:
    @staticmethod
    def log(
        *,
        provider: str,
        organization=None,
        url: str = "",
        method: str = "",
        service: str = "",
        operation: str = "",
        status_code: int | None = None,
        duration_ms: int | None = None,
        success: bool | None = None,
        error_code: str = "",
        error_message: str = "",
        request=None,
        resource_type: str = "",
        resource_id: str = "",
        idempotency_key: str = "",
        request_metadata: dict | None = None,
        response_metadata: dict | None = None,
    ) -> AuditExternalRequest:
        request_id, correlation_id = request_ids(request)
        url_host, url_path, url_hash = sanitize_url(url)
        inferred_success = status_code is not None and 200 <= status_code < 400
        return AuditExternalRequest.objects.create(
            organization_id=organization_id_for(organization),
            provider=provider,
            service=service,
            operation=operation,
            method=method.upper()[:12],
            url_host=url_host,
            url_path=url_path,
            url_hash=url_hash,
            status_code=status_code,
            duration_ms=duration_ms,
            success=inferred_success if success is None else success,
            error_code=error_code[:120],
            error_message=sanitize_error_message(error_message, limit=2000),
            request_id=request_id,
            correlation_id=correlation_id,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else "",
            idempotency_key=idempotency_key[:255],
            request_metadata=sanitize_payload(request_metadata or {}),
            response_metadata=sanitize_payload(response_metadata or {}),
        )
