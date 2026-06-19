from django.test import override_settings


@override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:3000"])
def test_cors_preflight_allows_organization_header(api_client):
    response = api_client.options(
        "/api/v1/auth/me/",
        HTTP_ORIGIN="http://localhost:3000",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,x-organization-id",
    )

    assert response.status_code == 200
    assert response["access-control-allow-origin"] == "http://localhost:3000"
    allowed = response["access-control-allow-headers"].lower()
    assert "authorization" in allowed
    assert "x-organization-id" in allowed
