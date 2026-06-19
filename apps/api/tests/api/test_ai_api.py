"""AI admin endpoint tests: permissions, envelope, tenant isolation."""

import pytest

from crm.ai.models import AIRun
from crm.ai.providers.fake_provider import FakeAIProvider
from crm.ai.services.ai_gateway import AIGateway
from crm.core.security.permissions import Role
from tests.factories.accounts import UserFactory
from tests.factories.ai import setup_ai_organization
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory, MessageFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory


def _member(role: Role = Role.OWNER):
    user = UserFactory()
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=role.value)
    return user, organization


def _auth(api_client, user, organization):
    api_client.force_authenticate(user=user)
    return {"HTTP_X_ORGANIZATION_ID": str(organization.id)}


@pytest.fixture(autouse=True)
def _reset_fake_provider():
    FakeAIProvider.reset()
    yield
    FakeAIProvider.reset()


def _make_run(organization):
    setup_ai_organization(organization)
    contact = ContactFactory(organization_id=organization.id, type="lead")
    conversation = ConversationFactory(organization_id=organization.id, contact=contact)
    message = MessageFactory(conversation=conversation, body="hola")
    return AIGateway.generate_sales_reply(conversation_id=conversation.id, message_id=message.id)


@pytest.mark.django_db
def test_runs_list_is_paginated_and_tenant_isolated(api_client):
    user, organization = _member(Role.OWNER)
    _other_user, other_org = _member(Role.OWNER)
    mine = _make_run(organization)
    _theirs = _make_run(other_org)

    response = api_client.get("/api/v1/ai/runs/", **_auth(api_client, user, organization))
    assert response.status_code == 200
    body = response.json()
    ids = {item["id"] for item in body["data"]}
    assert str(mine.run_id) in ids
    assert body["pagination"]["total"] == 1
    assert body["meta"]["request_id"]


@pytest.mark.django_db
def test_run_detail_does_not_expose_raw_response(api_client):
    user, organization = _member(Role.OWNER)
    result = _make_run(organization)

    response = api_client.get(
        f"/api/v1/ai/runs/{result.run_id}/", **_auth(api_client, user, organization)
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "raw_response" not in data
    assert data["prompt_key"] == "sales_agent_v1"
    assert data["prompt_version_number"] == 1

    messages = api_client.get(
        f"/api/v1/ai/runs/{result.run_id}/messages/", **_auth(api_client, user, organization)
    )
    assert messages.status_code == 200
    roles = {message["role"] for message in messages.json()["data"]}
    assert "system" in roles
    assert "assistant" in roles or "user" in roles


@pytest.mark.django_db
def test_viewer_cannot_read_ai_runs(api_client):
    user, organization = _member(Role.VIEWER)
    response = api_client.get("/api/v1/ai/runs/", **_auth(api_client, user, organization))
    assert response.status_code == 403


@pytest.mark.django_db
def test_prompt_lifecycle_via_api(api_client):
    user, organization = _member(Role.OWNER)
    setup_ai_organization(organization)
    headers = _auth(api_client, user, organization)

    listing = api_client.get("/api/v1/ai/prompts/", **headers)
    assert listing.status_code == 200
    sales = next(item for item in listing.json()["data"] if item["key"] == "sales_agent_v1")
    assert sales["active_version"]["version"] == 1

    created = api_client.post(
        f"/api/v1/ai/prompts/{sales['id']}/versions/",
        {
            "system_prompt": "Nuevo prompt para {business_name}",
            "template": "Mensaje: {current_message}",
            "output_schema": sales["active_version"]["output_schema"],
            "change_notes": "ajuste de tono",
        },
        format="json",
        **headers,
    )
    assert created.status_code == 201
    version = created.json()["data"]
    assert version["version"] == 2
    assert version["status"] == "draft"

    activated = api_client.post(
        f"/api/v1/ai/prompts/{sales['id']}/versions/{version['id']}/activate/",
        {},
        format="json",
        **headers,
    )
    assert activated.status_code == 200
    assert activated.json()["data"]["status"] == "active"

    detail = api_client.get(f"/api/v1/ai/prompts/{sales['id']}/", **headers)
    assert detail.json()["data"]["active_version"]["version"] == 2


@pytest.mark.django_db
def test_tools_catalog_endpoint(api_client):
    user, organization = _member(Role.OWNER)
    response = api_client.get("/api/v1/ai/tools/", **_auth(api_client, user, organization))
    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["data"]}
    assert {
        "create_task",
        "update_lead",
        "create_ticket",
        "notify_owner",
        "send_whatsapp_message",
        "pause_conversation_ai",
        "create_call_request",
        "generate_image",
    } <= names


@pytest.mark.django_db
def test_usage_endpoints(api_client):
    user, organization = _member(Role.OWNER)
    _make_run(organization)
    headers = _auth(api_client, user, organization)

    totals = api_client.get("/api/v1/ai/usage/", **headers)
    assert totals.status_code == 200
    assert totals.json()["data"]["runs"] == 1

    by_purpose = api_client.get("/api/v1/ai/usage/by-purpose/", **headers)
    assert by_purpose.status_code == 200
    assert by_purpose.json()["data"][0]["purpose"] == "sales_reply"

    by_day = api_client.get("/api/v1/ai/usage/by-day/", **headers)
    assert by_day.status_code == 200
    assert len(by_day.json()["data"]) == 1


@pytest.mark.django_db
def test_evals_run_via_api(api_client):
    user, organization = _member(Role.OWNER)
    headers = _auth(api_client, user, organization)
    run = api_client.post(
        "/api/v1/ai/evals/run/", {"suite_name": "sales_agent"}, format="json", **headers
    )
    assert run.status_code == 200
    assert run.json()["data"]["total"] >= 6

    results = api_client.get("/api/v1/ai/evals/results/", **headers)
    assert results.status_code == 200
    assert results.json()["pagination"]["total"] >= 6


@pytest.mark.django_db
def test_model_config_activate_deactivates_siblings(api_client):
    user, organization = _member(Role.OWNER)
    provider = setup_ai_organization(organization, seed_prompts=False)
    headers = _auth(api_client, user, organization)

    listing = api_client.get("/api/v1/ai/model-configs/", **headers)
    sales_config = next(item for item in listing.json()["data"] if item["purpose"] == "sales_reply")
    created = api_client.post(
        "/api/v1/ai/model-configs/",
        {
            "provider": str(provider.id),
            "purpose": "sales_reply",
            "model_name": "fake-model-2",
            "temperature": "0.30",
            "max_tokens": 512,
            "timeout_seconds": 30,
            "is_active": False,
            "supports_tools": True,
            "supports_structured_outputs": True,
        },
        format="json",
        **headers,
    )
    assert created.status_code == 201
    new_id = created.json()["data"]["id"]

    activated = api_client.post(
        f"/api/v1/ai/model-configs/{new_id}/activate/", {}, format="json", **headers
    )
    assert activated.status_code == 200
    old = api_client.get(f"/api/v1/ai/model-configs/{sales_config['id']}/", **headers)
    assert old.json()["data"]["is_active"] is False


@pytest.mark.django_db
def test_run_retry_dispatches_task(api_client, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user, organization = _member(Role.OWNER)
    result = _make_run(organization)
    headers = _auth(api_client, user, organization)

    runs_before = AIRun.objects.filter(organization_id=organization.id).count()
    response = api_client.post(
        f"/api/v1/ai/runs/{result.run_id}/retry/", {}, format="json", **headers
    )
    assert response.status_code == 202
    assert AIRun.objects.filter(organization_id=organization.id).count() == runs_before + 1
