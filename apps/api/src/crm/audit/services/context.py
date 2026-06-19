from __future__ import annotations

from django.http import HttpRequest

from crm.core.observability.context import get_correlation_id, get_request_id


def client_ip(request: HttpRequest | None) -> str | None:
    if request is None:
        return None
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def request_user_agent(request: HttpRequest | None) -> str:
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")[:500]


def request_ids(request: HttpRequest | None) -> tuple[str, str]:
    if request is None:
        return get_request_id() or "", get_correlation_id() or ""
    request_id = getattr(request, "request_id", "") or get_request_id() or ""
    correlation_id = getattr(request, "correlation_id", "") or get_correlation_id() or request_id
    return request_id, correlation_id


def actor_type_for(actor=None, *, fallback: str = "system") -> str:
    if actor is None:
        return fallback
    if getattr(actor, "is_authenticated", False):
        return "user"
    return fallback


def actor_id_for(actor=None):
    return getattr(actor, "id", None) if actor is not None else None


def organization_id_for(organization=None):
    return getattr(organization, "id", organization)
