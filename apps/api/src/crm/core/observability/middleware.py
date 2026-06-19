from __future__ import annotations

import re
import time
import uuid

from django.http import HttpRequest, HttpResponse

from .context import clear_request_context, set_request_context
from .metrics import MetricsRecorder

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def sanitized_header(raw_value: str | None) -> str | None:
    if raw_value and _SAFE_ID_RE.match(raw_value):
        return raw_value
    return None


class RequestIDMiddleware:
    request_header = "HTTP_X_REQUEST_ID"
    correlation_header = "HTTP_X_CORRELATION_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = sanitized_header(request.META.get(self.request_header)) or str(uuid.uuid4())
        correlation_id = sanitized_header(request.META.get(self.correlation_header)) or request_id
        started = time.perf_counter()

        request.request_id = request_id
        request.correlation_id = correlation_id
        set_request_context(request_id=request_id, correlation_id=correlation_id)

        try:
            response = self.get_response(request)
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            MetricsRecorder.increment(
                "http_requests_total",
                path=request.path,
                method=request.method,
            )
            MetricsRecorder.gauge(
                "http_request_duration_ms",
                duration_ms,
                path=request.path,
                method=request.method,
            )
            clear_request_context()

        response["X-Request-ID"] = request_id
        response["X-Correlation-ID"] = correlation_id
        return response
