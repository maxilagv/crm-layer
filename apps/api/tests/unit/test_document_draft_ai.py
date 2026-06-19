"""DOCUMENT_DRAFT purpose: drafts a payload that DocumentService can render."""

import pytest

from crm.ai.domain.enums import AIPurpose
from crm.ai.schemas import schema_for_purpose
from crm.ai.schemas.document_draft import DocumentDraftSchema
from crm.ai.services.ai_gateway import AIGateway
from crm.documents.domain.payload import normalize_payload
from tests.factories.ai import setup_ai_organization
from tests.factories.organizations import OrganizationFactory


def test_schema_example_is_valid_and_registered():
    assert schema_for_purpose(AIPurpose.DOCUMENT_DRAFT.value) is DocumentDraftSchema
    model = DocumentDraftSchema.model_validate(DocumentDraftSchema.example)
    payload = model.model_dump(mode="json")
    # The validated payload must be consumable by the document renderer pipeline.
    normalized = normalize_payload(payload)
    assert normalized["title"]
    assert normalized["total"] > 0  # example has priced items + 21% tax


@pytest.mark.django_db
def test_generate_document_draft_returns_renderable_payload():
    organization = OrganizationFactory()
    setup_ai_organization(organization)

    result = AIGateway.generate_document_draft(
        organization_id=organization.id,
        owner_request="/propuesta para ACME: app de turnos, backend + web, 3 meses de soporte",
        doc_type="proposal",
        currency="ARS",
        tax_rate="21",
        default_terms="50% para iniciar, 50% contra entrega.",
    )

    assert result.succeeded
    assert result.purpose == AIPurpose.DOCUMENT_DRAFT.value
    data = result.data
    assert data["title"]
    assert "items" in data and "client" in data and "sections" in data
    # Feeds straight into the renderer pipeline.
    normalized = normalize_payload(data)
    assert normalized["total"] >= 0


@pytest.mark.django_db
def test_generate_document_draft_passes_to_document_service(settings, tmp_path):
    settings.MEDIA_PRIVATE_ROOT = str(tmp_path)
    organization = OrganizationFactory()
    setup_ai_organization(organization)

    result = AIGateway.generate_document_draft(
        organization_id=organization.id,
        owner_request="/propuesta para ACME: app de turnos",
        doc_type="proposal",
        currency="ARS",
        tax_rate="21",
    )
    assert result.succeeded

    from crm.documents.services.document_service import DocumentService

    doc = DocumentService.generate(
        organization=organization,
        doc_type="proposal",
        fmt="pdf",
        payload=result.data,
    )
    assert doc.media_asset_id is not None
    assert doc.title
