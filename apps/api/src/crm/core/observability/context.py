from __future__ import annotations

import uuid
from contextlib import contextmanager

from crm.core import request_context


def new_id() -> str:
    return str(uuid.uuid4())


def get_request_id() -> str | None:
    return request_context.get_request_id()


def get_correlation_id() -> str | None:
    return request_context.get_correlation_id()


def get_organization_id() -> str | None:
    return request_context.organization_id_var.get()


def get_user_id() -> str | None:
    return request_context.user_id_var.get()


def get_context() -> dict[str, str | None]:
    return {
        "request_id": get_request_id(),
        "correlation_id": get_correlation_id(),
        "organization_id": get_organization_id(),
        "user_id": get_user_id(),
    }


def set_request_context(
    *,
    request_id: str,
    correlation_id: str | None = None,
    organization_id: str | None = None,
    user_id: str | None = None,
) -> None:
    request_context.set_request_context(
        request_id=request_id,
        correlation_id=correlation_id or request_id,
        organization_id=organization_id,
        user_id=user_id,
    )


def set_organization_context(*, organization_id=None, user_id=None) -> None:
    set_request_context(
        request_id=get_request_id() or new_id(),
        correlation_id=get_correlation_id() or get_request_id() or new_id(),
        organization_id=str(organization_id) if organization_id else get_organization_id(),
        user_id=str(user_id) if user_id else get_user_id(),
    )


def clear_request_context() -> None:
    request_context.clear_request_context()


@contextmanager
def observability_context(**context):
    previous = get_context()
    set_request_context(
        request_id=context.get("request_id") or previous.get("request_id") or new_id(),
        correlation_id=context.get("correlation_id") or previous.get("correlation_id"),
        organization_id=context.get("organization_id") or previous.get("organization_id"),
        user_id=context.get("user_id") or previous.get("user_id"),
    )
    try:
        yield
    finally:
        if previous.get("request_id"):
            set_request_context(
                request_id=previous["request_id"],
                correlation_id=previous.get("correlation_id"),
                organization_id=previous.get("organization_id"),
                user_id=previous.get("user_id"),
            )
        else:
            clear_request_context()
