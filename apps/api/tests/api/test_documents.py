"""Phase 8 documents API: brand kit, generate (PDF/XLSX/PPTX), download, send, tool."""

import pytest

from crm.core.security.permissions import Role
from crm.documents.models import BrandKit, GeneratedDocument
from crm.media.models import MediaAsset
from tests.factories.accounts import UserFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory

PAYLOAD = {
    "title": "Propuesta de desarrollo",
    "subtitle": "App de gestión de turnos",
    "client": {"name": "ACME SRL", "contact": "Juan", "email": "juan@acme.com"},
    "intro": "Gracias por la oportunidad.",
    "sections": [{"heading": "Alcance", "body": "Backend + app web."}],
    "items": [
        {"description": "Desarrollo backend", "quantity": 1, "unit_price": "150000"},
        {"description": "Soporte mensual", "quantity": 3, "unit_price": "20000"},
    ],
    "currency": "ARS",
    "tax_rate": "21",
    "valid_until": "2026-07-01",
}


@pytest.fixture(autouse=True)
def _private_media(settings, tmp_path):
    settings.MEDIA_PRIVATE_ROOT = str(tmp_path / "private_media")


def _member(role: Role = Role.OWNER):
    user = UserFactory()
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=role.value)
    return user, organization


def _auth(api_client, user, organization):
    api_client.force_authenticate(user=user)
    return {"HTTP_X_ORGANIZATION_ID": str(organization.id)}


@pytest.mark.django_db
def test_brand_kit_get_and_patch(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    res = api_client.get("/api/v1/documents/brand-kit/", **headers)
    assert res.status_code == 200
    assert "primary_color" in res.json()["data"]

    patched = api_client.patch(
        "/api/v1/documents/brand-kit/",
        {"business_name": "Mi Estudio", "primary_color": "#123456"},
        format="json",
        **headers,
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["business_name"] == "Mi Estudio"
    assert BrandKit.objects.filter(organization_id=org.id).count() == 1


@pytest.mark.django_db
def test_brand_kit_requires_settings_manage(api_client):
    user, org = _member(Role.VIEWER)
    headers = _auth(api_client, user, org)
    assert api_client.get("/api/v1/documents/brand-kit/", **headers).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("fmt", ["pdf", "xlsx", "pptx"])
def test_generate_document(api_client, fmt):
    user, org = _member()
    headers = _auth(api_client, user, org)
    res = api_client.post(
        "/api/v1/documents/",
        {"doc_type": "proposal", "doc_format": fmt, "payload": PAYLOAD},
        format="json",
        **headers,
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["doc_format"] == fmt
    assert data["status"] == "ready"
    assert data["download_url"] and "token=" in data["download_url"]
    doc = GeneratedDocument.objects.get(id=data["id"])
    assert doc.media_asset_id is not None
    assert MediaAsset.objects.filter(id=doc.media_asset_id).exists()


@pytest.mark.django_db
def test_list_download_and_send(api_client):
    user, org = _member()
    headers = _auth(api_client, user, org)
    created = api_client.post(
        "/api/v1/documents/",
        {"doc_type": "quote", "doc_format": "pdf", "payload": PAYLOAD},
        format="json",
        **headers,
    ).json()["data"]
    doc_id = created["id"]

    listed = api_client.get("/api/v1/documents/?doc_type=quote", **headers)
    assert listed.status_code == 200
    assert listed.json()["pagination"]["total"] >= 1

    dl = api_client.get(f"/api/v1/documents/{doc_id}/download-url/", **headers)
    assert dl.status_code == 200
    assert "token=" in dl.json()["data"]["url"]

    sent = api_client.post(f"/api/v1/documents/{doc_id}/send/", **headers)
    assert sent.status_code == 200
    assert sent.json()["data"]["status"] == "sent"


@pytest.mark.django_db
def test_documents_are_organization_scoped(api_client):
    u1, org1 = _member()
    h1 = _auth(api_client, u1, org1)
    created = api_client.post(
        "/api/v1/documents/",
        {"doc_type": "proposal", "doc_format": "pdf", "payload": PAYLOAD},
        format="json",
        **h1,
    ).json()["data"]

    u2, org2 = _member()
    h2 = _auth(api_client, u2, org2)
    assert api_client.get(f"/api/v1/documents/{created['id']}/", **h2).status_code == 404


@pytest.mark.django_db
def test_generate_document_tool_creates_draft():
    from types import SimpleNamespace

    from crm.ai.tools.base import ToolContext
    from crm.documents.ai_tool import GenerateDocumentTool

    user = UserFactory()
    org = OrganizationFactory(owner=user)
    ctx = ToolContext(organization_id=org.id, ai_run=SimpleNamespace(id=None), actor=user)
    result = GenerateDocumentTool().execute(
        arguments={"doc_type": "proposal", "format": "pdf", "payload": PAYLOAD},
        context=ctx,
    )
    assert result["ok"] is True
    doc = GeneratedDocument.objects.get(id=result["document_id"])
    assert doc.status == "draft"
    assert doc.media_asset_id is not None
