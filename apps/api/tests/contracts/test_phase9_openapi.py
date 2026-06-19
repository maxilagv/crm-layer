import pytest


@pytest.mark.django_db
def test_openapi_contains_phase9_endpoints(api_client) -> None:
    response = api_client.get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/analytics/dashboard/" in schema["paths"]
    assert "/api/v1/analytics/ai-costs/" in schema["paths"]
    assert "/api/v1/audit/logs/" in schema["paths"]
    assert "/api/v1/audit/external-requests/" in schema["paths"]
    assert "/api/system/status/" in schema["paths"]
