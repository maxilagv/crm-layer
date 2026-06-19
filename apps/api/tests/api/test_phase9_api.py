"""Phase 9.4: project-brief API endpoint."""

import pytest

from crm.core.security.permissions import Role
from tests.factories.accounts import UserFactory
from tests.factories.ai import setup_ai_organization
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory, MessageFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory


def _owner_org():
    user = UserFactory()
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=Role.OWNER.value)
    return user, organization


@pytest.mark.django_db
def test_project_brief_endpoint(api_client):
    user, org = _owner_org()
    setup_ai_organization(org)
    contact = ContactFactory(organization_id=org.id)
    conversation = ConversationFactory(contact=contact)
    MessageFactory(conversation=conversation, body="Quieren una app de turnos, backend + web.")

    api_client.force_authenticate(user=user)
    res = api_client.post(
        "/api/v1/ai/project-briefs/",
        {"conversation_id": str(conversation.id), "deal_value_hint": "aprox 2M"},
        format="json",
        HTTP_X_ORGANIZATION_ID=str(org.id),
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["brief"]["title"]
    assert data["run_id"]


@pytest.mark.django_db
def test_project_brief_requires_conversation_id(api_client):
    user, org = _owner_org()
    api_client.force_authenticate(user=user)
    res = api_client.post(
        "/api/v1/ai/project-briefs/",
        {},
        format="json",
        HTTP_X_ORGANIZATION_ID=str(org.id),
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_project_brief_is_org_scoped(api_client):
    user, org = _owner_org()
    other = OrganizationFactory()
    contact = ContactFactory(organization_id=other.id)
    conversation = ConversationFactory(contact=contact)

    api_client.force_authenticate(user=user)
    res = api_client.post(
        "/api/v1/ai/project-briefs/",
        {"conversation_id": str(conversation.id)},
        format="json",
        HTTP_X_ORGANIZATION_ID=str(org.id),
    )
    assert res.status_code == 404
