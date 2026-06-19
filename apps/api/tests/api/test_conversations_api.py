import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from crm.conversations.constants import ConversationMode, ConversationStatus, MessageDirection
from crm.conversations.models import Message
from crm.core.security.permissions import Role
from tests.factories.accounts import UserFactory
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory, MessageFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory


def _member(role: Role = Role.OPERATOR):
    user = UserFactory()
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=role.value)
    return user, organization


def _auth(api_client, user, organization):
    api_client.force_authenticate(user=user)
    return {"HTTP_X_ORGANIZATION_ID": str(organization.id)}


@pytest.mark.django_db
def test_inbox_list_is_isolated_with_last_message_preview(api_client):
    user, organization = _member(Role.VIEWER)
    _other, other_org = _member(Role.OWNER)
    conversation = ConversationFactory(
        organization_id=organization.id,
        contact=ContactFactory(organization_id=organization.id, display_name="Juan"),
    )
    MessageFactory(conversation=conversation, body="Hola, quiero info")
    ConversationFactory(
        organization_id=other_org.id, contact=ContactFactory(organization_id=other_org.id)
    )

    response = api_client.get("/api/v1/conversations/", **_auth(api_client, user, organization))

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total"] == 1
    item = body["data"][0]
    assert item["contact"]["display_name"] == "Juan"
    assert item["last_message"]["body_preview"] == "Hola, quiero info"


@pytest.mark.django_db
def test_inbox_filters_by_status(api_client):
    user, organization = _member(Role.OPERATOR)
    ConversationFactory(organization_id=organization.id, status=ConversationStatus.OPEN)
    ConversationFactory(organization_id=organization.id, status=ConversationStatus.CLOSED)
    headers = _auth(api_client, user, organization)

    response = api_client.get("/api/v1/conversations/?status=closed", **headers)
    assert response.status_code == 200
    assert all(item["status"] == "closed" for item in response.json()["data"])


@pytest.mark.django_db
def test_conversation_detail_and_messages(api_client):
    user, organization = _member(Role.OPERATOR)
    headers = _auth(api_client, user, organization)
    conversation = ConversationFactory(organization_id=organization.id)
    MessageFactory(
        conversation=conversation,
        direction=MessageDirection.INBOUND,
        body="primero",
        raw_payload={"provider_secret": "TOPSECRET"},
    )
    MessageFactory(conversation=conversation, direction=MessageDirection.OUTBOUND, body="segundo")

    detail = api_client.get(f"/api/v1/conversations/{conversation.id}/", **headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == str(conversation.id)

    messages = api_client.get(f"/api/v1/conversations/{conversation.id}/messages/", **headers)
    assert messages.status_code == 200
    data = messages.json()["data"]
    assert [m["body"] for m in data] == ["primero", "segundo"]
    # raw_payload must never be exposed.
    assert "raw_payload" not in data[0]
    assert "TOPSECRET" not in messages.content.decode()


@pytest.mark.django_db
def test_send_message_creates_outbound_without_provider(api_client):
    user, organization = _member(Role.OPERATOR)
    headers = _auth(api_client, user, organization)
    conversation = ConversationFactory(organization_id=organization.id)

    response = api_client.post(
        f"/api/v1/conversations/{conversation.id}/send-message/",
        {"body": "Gracias por escribirnos"},
        format="json",
        **headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["direction"] == "outbound"
    assert data["status"] == "queued"
    assert "raw_payload" not in data

    conversation.refresh_from_db()
    assert conversation.last_outbound_at is not None
    assert Message.objects.filter(conversation=conversation, direction="outbound").count() == 1


@pytest.mark.django_db
def test_viewer_cannot_send_message(api_client):
    user, organization = _member(Role.VIEWER)
    conversation = ConversationFactory(organization_id=organization.id)
    response = api_client.post(
        f"/api/v1/conversations/{conversation.id}/send-message/",
        {"body": "Hola"},
        format="json",
        **_auth(api_client, user, organization),
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_takeover_pause_resume_via_api(api_client):
    user, organization = _member(Role.OPERATOR)
    headers = _auth(api_client, user, organization)
    contact = ContactFactory(organization_id=organization.id, type="lead")
    conversation = ConversationFactory(
        organization_id=organization.id, contact=contact, mode=ConversationMode.SALES_AI
    )

    takeover = api_client.post(
        f"/api/v1/conversations/{conversation.id}/takeover/", {}, format="json", **headers
    )
    assert takeover.status_code == 200
    assert takeover.json()["data"]["mode"] == "manual"
    assert takeover.json()["data"]["ai_enabled"] is False
    assert takeover.json()["data"]["assigned_user"]["id"] == str(user.id)

    pause = api_client.post(
        f"/api/v1/conversations/{conversation.id}/pause-ai/", {}, format="json", **headers
    )
    assert pause.json()["data"]["mode"] == "paused"

    resume = api_client.post(
        f"/api/v1/conversations/{conversation.id}/resume-ai/", {}, format="json", **headers
    )
    assert resume.json()["data"]["ai_enabled"] is True
    assert resume.json()["data"]["mode"] == "sales_ai"


@pytest.mark.django_db
def test_close_and_reopen_via_api(api_client):
    user, organization = _member(Role.OPERATOR)
    headers = _auth(api_client, user, organization)
    contact = ContactFactory(organization_id=organization.id, type="client")
    conversation = ConversationFactory(organization_id=organization.id, contact=contact)

    close = api_client.post(
        f"/api/v1/conversations/{conversation.id}/close/", {}, format="json", **headers
    )
    assert close.json()["data"]["status"] == "closed"

    reopen = api_client.post(
        f"/api/v1/conversations/{conversation.id}/reopen/", {}, format="json", **headers
    )
    assert reopen.json()["data"]["status"] == "open"
    assert reopen.json()["data"]["mode"] == "support_ai"


@pytest.mark.django_db
def test_viewer_cannot_takeover(api_client):
    user, organization = _member(Role.VIEWER)
    conversation = ConversationFactory(organization_id=organization.id)
    response = api_client.post(
        f"/api/v1/conversations/{conversation.id}/takeover/",
        {},
        format="json",
        **_auth(api_client, user, organization),
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_action_on_foreign_conversation_returns_404(api_client):
    user, organization = _member(Role.OPERATOR)
    _other, other_org = _member(Role.OWNER)
    foreign = ConversationFactory(organization_id=other_org.id)
    response = api_client.post(
        f"/api/v1/conversations/{foreign.id}/takeover/",
        {},
        format="json",
        **_auth(api_client, user, organization),
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_inbox_has_no_n_plus_one(api_client):
    user, organization = _member(Role.OPERATOR)
    headers = _auth(api_client, user, organization)
    # Warm up auth/membership caches so the comparison isolates per-row growth.
    api_client.get("/api/v1/conversations/", **headers)

    conversation = ConversationFactory(organization_id=organization.id)
    MessageFactory(conversation=conversation)
    with CaptureQueriesContext(connection) as small:
        first = api_client.get("/api/v1/conversations/", **headers)
    assert first.status_code == 200

    for _ in range(4):
        extra = ConversationFactory(organization_id=organization.id)
        MessageFactory(conversation=extra)
    with CaptureQueriesContext(connection) as large:
        second = api_client.get("/api/v1/conversations/", **headers)
    assert second.status_code == 200

    assert len(second.json()["data"]) == 5
    # Query count must not grow with the number of conversations.
    assert len(large.captured_queries) == len(small.captured_queries)
