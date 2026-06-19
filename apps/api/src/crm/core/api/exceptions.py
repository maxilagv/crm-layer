import logging
from typing import Any

from django.conf import settings
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.views import exception_handler

from .responses import error_response

logger = logging.getLogger(__name__)

ERROR_CODE_MAP = {
    "not_found": "resource_not_found",
    "permission_denied": "permission_denied",
    "not_authenticated": "not_authenticated",
    "authentication_failed": "authentication_failed",
    "method_not_allowed": "method_not_allowed",
    "not_acceptable": "not_acceptable",
    "unsupported_media_type": "unsupported_media_type",
    "throttled": "request_throttled",
    "parse_error": "parse_error",
    "invalid": "validation_error",
}


def _flatten_details(data: Any) -> Any:
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        return {}
    return data


def _message_from_data(data: Any) -> str:
    if isinstance(data, dict) and "detail" in data:
        return str(data["detail"])
    if isinstance(data, (list, dict)):
        return "Validation error"
    return str(data)


def _code_from_exception(exc: Exception) -> str:
    if isinstance(exc, Http404):
        return "resource_not_found"
    if isinstance(exc, exceptions.ValidationError):
        return "validation_error"
    code = getattr(exc, "default_code", "server_error")
    return ERROR_CODE_MAP.get(str(code), str(code))


def enveloped_exception_handler(exc: Exception, context: dict[str, Any]):
    """Global DRF handler: every API error uses the standard error envelope."""
    response = exception_handler(exc, context)
    request = context.get("request")

    if response is None:
        # Not an API exception: a real bug. Log it; in DEBUG let Django render
        # the traceback page, otherwise return a safe enveloped 500.
        logger.exception(
            "Unhandled exception in API view",
            extra={"event": "api.unhandled_exception"},
        )
        if settings.DEBUG:
            return None
        return error_response(
            request,
            code="server_error",
            message="Internal server error",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = _code_from_exception(exc)
    return error_response(
        request,
        code=code,
        message=_message_from_data(response.data),
        details=_flatten_details(response.data),
        status=response.status_code,
        headers=dict(response.headers),
    )
