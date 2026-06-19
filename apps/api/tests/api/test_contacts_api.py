import pytest

from crm.core.security.permissions import Role
from tests.factories.accounts import UserFactory
from tests.factories.contacts import ContactFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory

AR_LANDLINE = "+541143215678"


def _member(role: Role = Role.OPERATOR):
    user = UserFactory()
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=role.value)
    return user, organization


def _auth(api_client, user, organization):
    api_client.force_authenticate(user=user)
    return {"HTTP_X_ORGANIZATION_ID": str(organization.id)}


@pytest.mark.django_db
def test_create_contact_via_api(api_client):
    user, organization = _member(Role.OPERATOR)
    response = api_client.post(
        "/api/v1/contacts/",
        {"display_name": "Juan", "type": "lead", "phones": [{"phone": "11 4321-5678"}]},
        format="json",
        **_auth(api_client, user, organization),
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["display_name"] == "Juan"
    assert data["type"] == "lead"
    assert data["primary_phone"] == AR_LANDLINE
    assert response.json()["meta"]["request_id"]


@pytest.mark.django_db
def test_viewer_cannot_create_contact(api_client):
    user, organization = _member(Role.VIEWER)
    response = api_client.post(
        "/api/v1/contacts/",
        {"display_name": "Nope"},
        format="json",
        **_auth(api_client, user, organization),
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_contacts_list_is_paginated_and_tenant_isolated(api_client):
    user, organization = _member(Role.OPERATOR)
    _other_user, other_org = _member(Role.OWNER)
    ContactFactory(organization_id=organization.id, display_name="Mine")
    ContactFactory(organization_id=other_org.id, display_name="Theirs")

    response = api_client.get("/api/v1/contacts/", **_auth(api_client, user, organization))

    assert response.status_code == 200
    body = response.json()
    names = {item["display_name"] for item in body["data"]}
    assert "Mine" in names
    assert "Theirs" not in names
    assert body["pagination"]["total"] == 1
    assert body["meta"]["request_id"]


@pytest.mark.django_db
def test_invalid_phone_returns_validation_error(api_client):
    user, organization = _member(Role.OPERATOR)
    response = api_client.post(
        "/api/v1/contacts/",
        {"display_name": "X", "phones": [{"phone": "not-a-phone"}]},
        format="json",
        **_auth(api_client, user, organization),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.django_db
def test_duplicate_phone_returns_conflict(api_client):
    user, organization = _member(Role.OPERATOR)
    headers = _auth(api_client, user, organization)
    api_client.post(
        "/api/v1/contacts/",
        {"display_name": "A", "phones": [{"phone": AR_LANDLINE}]},
        format="json",
        **headers,
    )
    response = api_client.post(
        "/api/v1/contacts/",
        {"display_name": "B", "phones": [{"phone": "11 4321-5678"}]},
        format="json",
        **headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "phone_already_exists"


@pytest.mark.django_db
def test_contact_detail_is_not_cross_tenant(api_client):
    user, organization = _member(Role.OPERATOR)
    _other_user, other_org = _member(Role.OWNER)
    foreign = ContactFactory(organization_id=other_org.id)

    response = api_client.get(
        f"/api/v1/contacts/{foreign.id}/", **_auth(api_client, user, organization)
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_patch_contact(api_client):
    user, organization = _member(Role.OPERATOR)
    contact = ContactFactory(organization_id=organization.id, display_name="Old", type="lead")

    response = api_client.patch(
        f"/api/v1/contacts/{contact.id}/",
        {"display_name": "New", "type": "client"},
        format="json",
        **_auth(api_client, user, organization),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["display_name"] == "New"
    assert data["type"] == "client"


@pytest.mark.django_db
def test_soft_delete_hides_contact_from_list(api_client):
    user, organization = _member(Role.OPERATOR)
    headers = _auth(api_client, user, organization)
    contact = ContactFactory(organization_id=organization.id, display_name="Bye")

    delete = api_client.delete(f"/api/v1/contacts/{contact.id}/", **headers)
    assert delete.status_code == 200

    listing = api_client.get("/api/v1/contacts/", **headers)
    ids = {item["id"] for item in listing.json()["data"]}
    assert str(contact.id) not in ids


@pytest.mark.django_db
def test_add_note_and_tag(api_client):
    user, organization = _member(Role.OPERATOR)
    headers = _auth(api_client, user, organization)
    contact = ContactFactory(organization_id=organization.id)

    note = api_client.post(
        f"/api/v1/contacts/{contact.id}/notes/",
        {"body": "Called the client", "visibility": "team"},
        format="json",
        **headers,
    )
    assert note.status_code == 201
    assert note.json()["data"]["body"] == "Called the client"
    assert note.json()["data"]["author"]["id"] == str(user.id)

    tag = api_client.post(
        f"/api/v1/contacts/{contact.id}/tags/",
        {"name": "VIP Client", "color": "#ff0000"},
        format="json",
        **headers,
    )
    assert tag.status_code == 201
    slugs = {item["slug"] for item in tag.json()["data"]}
    assert "vip-client" in slugs


@pytest.mark.django_db
def test_merge_endpoint(api_client):
    user, organization = _member(Role.OPERATOR)
    headers = _auth(api_client, user, organization)
    target = ContactFactory(organization_id=organization.id, display_name="Target")
    source = ContactFactory(organization_id=organization.id, display_name="Source")

    response = api_client.post(
        "/api/v1/contacts/merge/",
        {"source_contact_id": str(source.id), "target_contact_id": str(target.id)},
        format="json",
        **headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(target.id)

    source.refresh_from_db()
    assert source.deleted_at is not None
