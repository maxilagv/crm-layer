from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from crm.accounts.models import APIKey
from crm.accounts.services.api_keys import create_api_key
from crm.audit.models import AuditEvent
from crm.core.security.permissions import PermissionCode, Role
from crm.organizations.models import Membership
from tests.factories.accounts import UserFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory


def _member(role: Role = Role.OWNER):
    user = UserFactory(password="correct-password")
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=role.value)
    return user, organization


def _auth(api_client, user, organization):
    api_client.force_authenticate(user=user)
    return {"HTTP_X_ORGANIZATION_ID": str(organization.id)}


@pytest.mark.django_db
def test_login_success(api_client) -> None:
    cache.clear()
    user, _organization = _member()

    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": user.email.upper(), "password": "correct-password"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["data"]["token_type"] == "Bearer"
    assert response.json()["data"]["access"]
    assert response.json()["data"]["refresh"]
    assert AuditEvent.objects.filter(event_type="login_succeeded", actor_id=user.id).exists()


@pytest.mark.django_db
def test_login_failed_is_logged(api_client) -> None:
    cache.clear()
    user, _organization = _member()

    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "bad-password"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid credentials"
    assert AuditEvent.objects.filter(
        event_type="login_failed",
        metadata__email=user.email,
    ).exists()


@pytest.mark.django_db
def test_auth_me(api_client) -> None:
    user, organization = _member(Role.ADMIN)

    response = api_client.get("/api/v1/auth/me/", **_auth(api_client, user, organization))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["user"]["email"] == user.email
    assert data["organization"]["id"] == str(organization.id)
    assert data["membership"]["role"] == Role.ADMIN.value
    assert PermissionCode.SETTINGS_MANAGE.value in data["permissions"]


@pytest.mark.django_db
def test_permission_denied_is_audited(api_client) -> None:
    user, organization = _member(Role.VIEWER)

    response = api_client.patch(
        "/api/v1/settings/business-profile/",
        {"business_name": "Blocked"},
        format="json",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 403
    assert AuditEvent.objects.filter(
        event_type="permission_denied",
        actor_id=user.id,
        organization_id=organization.id,
        metadata__permission=PermissionCode.SETTINGS_MANAGE.value,
    ).exists()


@pytest.mark.django_db
def test_organization_data_isolation(api_client) -> None:
    owner, organization = _member(Role.OWNER)
    other_owner, other_organization = _member(Role.OWNER)

    response = api_client.get("/api/v1/users/", **_auth(api_client, owner, organization))

    assert response.status_code == 200
    emails = {item["email"] for item in response.json()["data"]}
    assert owner.email in emails
    assert other_owner.email not in emails

    blocked = api_client.get(
        "/api/v1/users/",
        **_auth(api_client, owner, other_organization),
    )
    assert blocked.status_code == 403


@pytest.mark.django_db
def test_api_key_is_hashed_and_visible_once(api_client) -> None:
    user, organization = _member(Role.OWNER)

    response = api_client.post(
        "/api/v1/api-keys/",
        {
            "name": "Worker",
            "scopes": [PermissionCode.SETTINGS_MANAGE.value],
            "expires_at": (timezone.now() + timedelta(days=1)).isoformat(),
        },
        format="json",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["key"].startswith("acrm_")

    api_key = APIKey.objects.get(id=data["id"])
    assert api_key.hashed_key != data["key"]
    assert api_key.hashed_key == APIKey.hash_key(data["key"])

    list_response = api_client.get("/api/v1/api-keys/", **_auth(api_client, user, organization))
    assert list_response.status_code == 200
    assert "key" not in list_response.json()["data"][0]


@pytest.mark.django_db
def test_api_key_scope_restricts_access(api_client) -> None:
    user, organization = _member(Role.OWNER)
    created = create_api_key(
        organization=organization,
        name="Read only",
        scopes=[PermissionCode.CONTACTS_VIEW.value],
        created_by=user,
    )

    response = api_client.patch(
        "/api/v1/settings/sales-policy/",
        {"main_sales_goal": "Close consultative deals"},
        format="json",
        HTTP_X_API_KEY=created.raw_key,
        HTTP_X_ORGANIZATION_ID=str(organization.id),
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_business_profile_update(api_client) -> None:
    user, organization = _member(Role.ADMIN)

    response = api_client.patch(
        "/api/v1/settings/business-profile/",
        {
            "business_name": "CRM Layer",
            "timezone": "America/Argentina/Buenos_Aires",
            "services_offered": ["CRM operativo", "Automatizacion WhatsApp"],
        },
        format="json",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["business_name"] == "CRM Layer"
    assert data["services_offered"] == ["CRM operativo", "Automatizacion WhatsApp"]


@pytest.mark.django_db
def test_sales_policy_update(api_client) -> None:
    user, organization = _member(Role.ADMIN)

    response = api_client.patch(
        "/api/v1/settings/sales-policy/",
        {"price_min": "100.00", "price_max": "300.00", "can_quote_prices": True},
        format="json",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 200
    assert response.json()["data"]["price_min"] == "100.00"
    assert response.json()["data"]["price_max"] == "300.00"


@pytest.mark.django_db
def test_support_policy_update(api_client) -> None:
    user, organization = _member(Role.ADMIN)

    response = api_client.patch(
        "/api/v1/settings/support-policy/",
        {
            "support_hours": "Lunes a viernes, 9 a 18",
            "urgent_keywords": ["caido", "no funciona"],
        },
        format="json",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 200
    assert response.json()["data"]["urgent_keywords"] == ["caido", "no funciona"]


@pytest.mark.django_db
def test_settings_audit_log_created(api_client) -> None:
    user, organization = _member(Role.ADMIN)

    response = api_client.patch(
        "/api/v1/settings/ai-policy/",
        {"default_provider": "anthropic", "temperature": "0.40"},
        format="json",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 200
    event = AuditEvent.objects.get(
        event_type="settings_updated",
        organization_id=organization.id,
        resource_type="settings_ai_behavior_policy",
    )
    assert event.changes["default_provider"]["after"] == "anthropic"
    assert event.actor_id == user.id


@pytest.mark.django_db
def test_viewer_cannot_create_user(api_client) -> None:
    user, organization = _member(Role.VIEWER)

    response = api_client.post(
        "/api/v1/users/",
        {
            "email": "new-user@example.com",
            "password": "secret-password-123",
            "name": "New User",
            "role": Role.OPERATOR.value,
        },
        format="json",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 403
    assert Membership.objects.filter(user__email="new-user@example.com").exists() is False
