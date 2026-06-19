from typing import Any

from rest_framework.response import Response


def get_request_id(request) -> str | None:
    return getattr(request, "request_id", None)


def meta_for_request(request) -> dict[str, Any]:
    return {"request_id": get_request_id(request)}


def success_response(
    request,
    data: Any,
    *,
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> Response:
    return Response(
        {"data": data, "meta": meta_for_request(request)},
        status=status,
        headers=headers,
    )


def error_response(
    request,
    *,
    code: str,
    message: str,
    details: Any | None = None,
    status: int = 400,
    headers: dict[str, str] | None = None,
) -> Response:
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "meta": meta_for_request(request),
    }
    return Response(payload, status=status, headers=headers)
