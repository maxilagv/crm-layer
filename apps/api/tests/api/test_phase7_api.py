"""Phase 7 API: clients, support tickets, media and image generation.

Covers the happy paths, ticket lifecycle actions, organization isolation and
permission gating. storage_key is never exposed; signed URLs carry a token.
"""

import pytest

from crm.core.security.permissions import Role
from crm.media.domain.enums import ImageGenerationStatus
from crm.support.domain.enums import TicketStatus
from crm.support.models import SupportTicket
from tests.factories.accounts import UserFactory
from tests.factories.clients import ClientFactory
from tests.factories.contacts import ContactFactory
from tests.factories.media import MediaAssetFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory


@pytest.fixture(autouse=True)
def _private_media(settings, tmp_path):
    settings.MEDIA_PRIVATE_ROOT = str(tmp_path / "private_media")


def _member(role: Role = Role.OPERATOR):
    user = UserFactory()
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=role.value)
    return user, organization


def _auth(api_client, user, organization):
    api_client.force_authenticate(user=user)
    return {"HTTP_X_ORGANIZATION_ID": str(organization.id)}


# ----------------------------------------------------------------- clients


@pytest.mark.django_db
def test_create_and_list_clients(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    contact = ContactFactory(organization_id=org.id)

    created = api_client.post(
        "/api/v1/clients/",
        {"contact_id": str(contact.id), "display_name": "ACME", "support_level": "vip"},
        format="json",
        **headers,
    )
    assert created.status_code == 201
    assert created.json()["data"]["support_level"] == "vip"

    listed = api_client.get("/api/v1/clients/", **headers)
    assert listed.status_code == 200
    assert listed.json()["pagination"]["total"] == 1


@pytest.mark.django_db
def test_client_detail_is_organization_scoped(api_client):
    _user_a, org_a = _member()
    client = ClientFactory(organization_id=org_a.id)
    # A member of another org cannot see it.
    user_b, org_b = _member()
    headers_b = _auth(api_client, user_b, org_b)
    response = api_client.get(f"/api/v1/clients/{client.id}/", **headers_b)
    assert response.status_code == 404


@pytest.mark.django_db
def test_update_client_status(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    client = ClientFactory(organization_id=org.id)
    response = api_client.patch(
        f"/api/v1/clients/{client.id}/", {"status": "paused"}, format="json", **headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "paused"


@pytest.mark.django_db
def test_viewer_cannot_create_client(api_client):
    user, org = _member(Role.VIEWER)
    headers = _auth(api_client, user, org)
    contact = ContactFactory(organization_id=org.id)
    response = api_client.post(
        "/api/v1/clients/", {"contact_id": str(contact.id)}, format="json", **headers
    )
    assert response.status_code == 403


# ------------------------------------------------------------- support tickets


@pytest.mark.django_db
def test_create_ticket_and_lifecycle(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    contact = ContactFactory(organization_id=org.id)

    created = api_client.post(
        "/api/v1/tickets/",
        {"contact_id": str(contact.id), "title": "No carga el panel", "description": "Error 500"},
        format="json",
        **headers,
    )
    assert created.status_code == 201
    ticket_id = created.json()["data"]["id"]

    # Assign to self (an active member), then resolve, then reopen.
    assigned = api_client.post(
        f"/api/v1/tickets/{ticket_id}/assign/", {"user_id": str(user.id)}, format="json", **headers
    )
    assert assigned.status_code == 200
    assert assigned.json()["data"]["assigned_user_id"] == str(user.id)

    resolved = api_client.post(
        f"/api/v1/tickets/{ticket_id}/resolve/",
        {"summary": "Reiniciamos el servicio"},
        format="json",
        **headers,
    )
    assert resolved.status_code == 200
    assert resolved.json()["data"]["status"] == TicketStatus.RESOLVED.value

    reopened = api_client.post(
        f"/api/v1/tickets/{ticket_id}/reopen/",
        {"reason": "volvió a fallar"},
        format="json",
        **headers,
    )
    assert reopened.status_code == 200
    assert reopened.json()["data"]["status"] == TicketStatus.IN_PROGRESS.value


@pytest.mark.django_db
def test_ticket_comment_created(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    contact = ContactFactory(organization_id=org.id)
    created = api_client.post(
        "/api/v1/tickets/",
        {"contact_id": str(contact.id), "title": "Consulta"},
        format="json",
        **headers,
    )
    ticket_id = created.json()["data"]["id"]
    response = api_client.post(
        f"/api/v1/tickets/{ticket_id}/comments/",
        {"body": "Investigando", "visibility": "internal"},
        format="json",
        **headers,
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_viewer_cannot_list_tickets(api_client):
    user, org = _member(Role.VIEWER)
    headers = _auth(api_client, user, org)
    response = api_client.get("/api/v1/tickets/", **headers)
    assert response.status_code == 403


@pytest.mark.django_db
def test_ticket_is_organization_scoped(api_client):
    _user_a, org_a = _member()
    contact = ContactFactory(organization_id=org_a.id)
    ticket = SupportTicket.objects.create(
        organization_id=org_a.id, contact=contact, title="x", description="y"
    )
    user_b, org_b = _member()
    headers_b = _auth(api_client, user_b, org_b)
    response = api_client.get(f"/api/v1/tickets/{ticket.id}/", **headers_b)
    assert response.status_code == 404


# ----------------------------------------------------------------- media


@pytest.mark.django_db
def test_media_list_and_signed_download_url(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    asset = MediaAssetFactory(organization_id=org.id)

    listed = api_client.get("/api/v1/media/assets/", **headers)
    assert listed.status_code == 200
    # The serialized asset never leaks the storage_key.
    payload = listed.json()["data"][0]
    assert "storage_key" not in payload

    signed = api_client.get(f"/api/v1/media/assets/{asset.id}/download-url/", **headers)
    assert signed.status_code == 200
    data = signed.json()["data"]
    assert "token=" in data["url"]
    assert asset.storage_key not in data["url"]
    assert data["expires_in"] > 0


@pytest.mark.django_db
def test_media_asset_is_organization_scoped(api_client):
    _user_a, org_a = _member()
    asset = MediaAssetFactory(organization_id=org_a.id)
    user_b, org_b = _member()
    headers_b = _auth(api_client, user_b, org_b)
    response = api_client.get(f"/api/v1/media/assets/{asset.id}/", **headers_b)
    assert response.status_code == 404


# ----------------------------------------------------------- image generation


@pytest.mark.django_db
def test_request_image_generation(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    response = api_client.post(
        "/api/v1/image-generations/",
        {"prompt": "Portada para propuesta", "image_type": "proposal_cover", "aspect_ratio": "1:1"},
        format="json",
        **headers,
    )
    assert response.status_code == 202
    data = response.json()["data"]
    assert data["status"] == ImageGenerationStatus.PENDING.value
    assert "id" in data
