from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
organization_id_var: ContextVar[str | None] = ContextVar("organization_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def get_request_id() -> str | None:
    return request_id_var.get()


def get_correlation_id() -> str | None:
    return correlation_id_var.get()


def set_request_context(
    *,
    request_id: str,
    correlation_id: str,
    organization_id: str | None = None,
    user_id: str | None = None,
) -> None:
    request_id_var.set(request_id)
    correlation_id_var.set(correlation_id)
    organization_id_var.set(organization_id)
    user_id_var.set(user_id)


def clear_request_context() -> None:
    request_id_var.set(None)
    correlation_id_var.set(None)
    organization_id_var.set(None)
    user_id_var.set(None)
