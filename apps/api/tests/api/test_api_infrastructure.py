import uuid

import pytest
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from crm.core.api.exceptions import enveloped_exception_handler
from crm.core.api.pagination import StandardPagination


def test_request_id_header_is_reused() -> None:
    response = APIClient().get("/api/health/live/", HTTP_X_REQUEST_ID="req-123")

    assert response["X-Request-ID"] == "req-123"
    assert response.json()["meta"]["request_id"] == "req-123"


def test_request_id_is_generated_when_missing() -> None:
    response = APIClient().get("/api/health/live/")

    generated = response["X-Request-ID"]
    assert uuid.UUID(generated)  # well-formed UUID
    assert response.json()["meta"]["request_id"] == generated


def test_unsafe_request_id_header_is_replaced() -> None:
    response = APIClient().get("/api/health/live/", HTTP_X_REQUEST_ID="bad\nvalue {}")

    assert uuid.UUID(response["X-Request-ID"])


def test_correlation_id_falls_back_to_request_id() -> None:
    response = APIClient().get("/api/health/live/", HTTP_X_REQUEST_ID="req-456")

    assert response["X-Correlation-ID"] == "req-456"


def test_correlation_id_header_is_respected() -> None:
    response = APIClient().get(
        "/api/health/live/",
        HTTP_X_REQUEST_ID="req-1",
        HTTP_X_CORRELATION_ID="corr-1",
    )

    assert response["X-Correlation-ID"] == "corr-1"


def test_error_response_format() -> None:
    factory = APIRequestFactory()
    django_request = factory.get("/missing", HTTP_X_REQUEST_ID="req-error")
    django_request.request_id = "req-error"
    request = Request(django_request)

    response = enveloped_exception_handler(NotFound("Resource not found"), {"request": request})

    assert response.status_code == 404
    assert response.data == {
        "error": {
            "code": "resource_not_found",
            "message": "Resource not found",
            "details": {},
        },
        "meta": {"request_id": "req-error"},
    }


def test_pagination_format() -> None:
    factory = APIRequestFactory()
    django_request = factory.get("/items?page=1&page_size=2", HTTP_X_REQUEST_ID="req-page")
    django_request.request_id = "req-page"
    request = Request(django_request)
    paginator = StandardPagination()

    page = paginator.paginate_queryset([1, 2, 3], request)
    response = paginator.get_paginated_response(page)

    assert response.data == {
        "data": [1, 2],
        "pagination": {
            "page": 1,
            "page_size": 2,
            "total": 3,
            "has_next": True,
        },
        "meta": {"request_id": "req-page"},
    }


@pytest.mark.django_db
def test_openapi_schema_is_available() -> None:
    response = APIClient().get("/api/schema/")

    assert response.status_code == 200
    assert "AI CRM API" in response.content.decode()
