"""Settings-facing integration endpoints: AI providers + WhatsApp connection."""

import pytest

from crm.core.security.permissions import Role
from tests.factories.accounts import UserFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory


def _member(role: Role = Role.OWNER):
    user = UserFactory()
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=role.value)
    return user, organization


def _auth(api_client, user, organization):
    api_client.force_authenticate(user=user)
    return {"HTTP_X_ORGANIZATION_ID": str(organization.id)}


# ----------------------------------------------------------------- AI providers


@pytest.mark.django_db
def test_ai_provider_crud(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)

    created = api_client.post(
        "/api/v1/ai/providers/",
        {"name": "OpenAI prod", "provider_type": "openai", "priority": 50},
        format="json",
        **headers,
    )
    assert created.status_code == 201
    provider_id = created.json()["data"]["id"]
    assert created.json()["data"]["is_enabled"] is True

    listed = api_client.get("/api/v1/ai/providers/", **headers)
    assert listed.status_code == 200
    assert any(p["id"] == provider_id for p in listed.json()["data"])

    patched = api_client.patch(
        f"/api/v1/ai/providers/{provider_id}/",
        {"is_enabled": False},
        format="json",
        **headers,
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["is_enabled"] is False


@pytest.mark.django_db
def test_ai_connection_status_reflects_env(api_client, settings):
    user, org = _member()
    headers = _auth(api_client, user, org)
    settings.OPENAI_API_KEY = "sk-test"
    settings.ANTHROPIC_API_KEY = ""

    res = api_client.get("/api/v1/ai/connection/", **headers)
    assert res.status_code == 200
    by_type = {p["provider_type"]: p for p in res.json()["data"]["providers"]}
    assert by_type["openai"]["credential_configured"] is True
    assert by_type["anthropic"]["credential_configured"] is False
    assert by_type["fake"]["credential_configured"] is True  # no env var needed


# -------------------------------------------------------------- WhatsApp connect


@pytest.mark.django_db
def test_whatsapp_account_and_number_registration(api_client, settings):
    user, org = _member()
    headers = _auth(api_client, user, org)
    settings.WHATSAPP_ACCESS_TOKEN = "tok"

    account = api_client.post(
        "/api/v1/whatsapp/accounts/",
        {"waba_id": "123456", "name": "Mi WABA"},
        format="json",
        **headers,
    )
    assert account.status_code == 201
    account_id = account.json()["data"]["id"]

    number = api_client.post(
        "/api/v1/whatsapp/phone-numbers/",
        {
            "business_account_id": account_id,
            "phone_number_id": "987654",
            "display_phone_number": "+54 11 5555-5555",
        },
        format="json",
        **headers,
    )
    assert number.status_code == 201
    assert number.json()["data"]["business_account_id"] == account_id

    status = api_client.get("/api/v1/whatsapp/connection/", **headers)
    assert status.status_code == 200
    data = status.json()["data"]
    assert data["accounts"] == 1
    assert data["phone_numbers"] == 1
    assert data["credentials"]["access_token"] is True
    assert data["connected"] is True


@pytest.mark.django_db
def test_whatsapp_number_rejects_foreign_account(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    # Account belongs to a different organization.
    _other_user, other_org = _member()
    from crm.whatsapp.models import WhatsAppBusinessAccount

    foreign = WhatsAppBusinessAccount.objects.create(
        organization_id=other_org.id, waba_id="999", name="Otra"
    )
    res = api_client.post(
        "/api/v1/whatsapp/phone-numbers/",
        {"business_account_id": str(foreign.id), "phone_number_id": "111"},
        format="json",
        **headers,
    )
    assert res.status_code == 400


# ------------------------------------------------------------------ permissions


@pytest.mark.django_db
def test_settings_endpoints_require_settings_manage(api_client):
    user, org = _member(Role.VIEWER)
    headers = _auth(api_client, user, org)
    assert api_client.get("/api/v1/ai/providers/", **headers).status_code == 403
    assert api_client.get("/api/v1/ai/connection/", **headers).status_code == 403
    assert api_client.get("/api/v1/whatsapp/connection/", **headers).status_code == 403
    assert api_client.get("/api/v1/settings/prospecting-policy/", **headers).status_code == 403


@pytest.mark.django_db
def test_prospecting_policy_settings_get_and_patch(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)

    initial = api_client.get("/api/v1/settings/prospecting-policy/", **headers)
    assert initial.status_code == 200
    assert initial.json()["data"]["agent_paused"] is False
    assert initial.json()["data"]["send_start_hour"] == 9

    patched = api_client.patch(
        "/api/v1/settings/prospecting-policy/",
        {
            "agent_paused": True,
            "send_start_hour": 8,
            "send_cutoff_hour": 16,
            "org_daily_cap": 12,
        },
        format="json",
        **headers,
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["agent_paused"] is True
    assert patched.json()["data"]["send_start_hour"] == 8
    assert patched.json()["data"]["send_cutoff_hour"] == 16
    assert patched.json()["data"]["org_daily_cap"] == 12


@pytest.mark.django_db
def test_ai_providers_are_organization_scoped(api_client):
    user_a, org_a = _member()
    headers_a = _auth(api_client, user_a, org_a)
    api_client.post(
        "/api/v1/ai/providers/",
        {"name": "A", "provider_type": "openai"},
        format="json",
        **headers_a,
    )
    user_b, org_b = _member()
    headers_b = _auth(api_client, user_b, org_b)
    listed_b = api_client.get("/api/v1/ai/providers/", **headers_b)
    assert listed_b.status_code == 200
    assert listed_b.json()["data"] == []
