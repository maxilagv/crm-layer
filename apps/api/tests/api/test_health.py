import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from crm.core.api import health


@pytest.mark.django_db
def test_health_endpoint() -> None:
    response = APIClient().get(reverse("health"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "ok"
    assert payload["meta"]["request_id"]


def test_live_endpoint_does_not_require_dependencies() -> None:
    response = APIClient().get(reverse("health-live"))

    assert response.status_code == 200
    assert response.json()["data"] == {"status": "ok"}


@pytest.mark.django_db
def test_ready_endpoint_with_db() -> None:
    response = APIClient().get(reverse("health-ready"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["checks"]["database"]["status"] == "ok"
    assert payload["data"]["checks"]["redis"]["status"] == "ok"


@pytest.mark.django_db
def test_ready_endpoint_returns_503_when_database_is_down(monkeypatch) -> None:
    def broken_database() -> dict[str, str]:
        raise RuntimeError("connection refused: postgres://user:secret@db:5432/app")

    monkeypatch.setattr(health, "_check_database", broken_database)

    response = APIClient().get(reverse("health-ready"))

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "service_unavailable"
    checks = payload["error"]["details"]["checks"]
    assert checks["database"]["status"] == "error"
    # The response must not leak connection strings or secrets.
    assert "secret" not in response.content.decode()


def test_version_endpoint() -> None:
    response = APIClient().get(reverse("version"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["version"]
    assert payload["data"]["commit"]
    assert payload["data"]["build_date"]
    assert payload["data"]["environment"] == "test"
    assert payload["meta"]["request_id"]
