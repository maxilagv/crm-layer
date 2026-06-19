"""WhatsApp bridge endpoints: inbound -> AI reply, event/status (QR)."""

import pytest

from crm.ai.providers.fake_provider import FakeAIProvider
from crm.conversations.models import Message
from crm.core.security.permissions import Role
from crm.prospecting.domain.enums import CampaignStatus, ProspectStatus
from crm.prospecting.models import Prospect, ProspectingCampaign
from crm.prospecting.services.outreach import ProspectOutreachService
from tests.factories.accounts import UserFactory
from tests.factories.ai import setup_ai_organization
from tests.factories.organizations import MembershipFactory, OrganizationFactory

SECRET = "s3cret-bridge"


@pytest.fixture(autouse=True)
def _reset_fake():
    FakeAIProvider.reset()
    yield
    FakeAIProvider.reset()


@pytest.fixture(autouse=True)
def _bridge_secret(settings):
    settings.WA_BRIDGE_SHARED_SECRET = SECRET


def _secret_headers():
    return {"HTTP_X_BRIDGE_SECRET": SECRET}


@pytest.mark.django_db
def test_inbound_requires_secret(api_client):
    org = OrganizationFactory()
    res = api_client.post(
        "/api/v1/whatsapp/bridge/inbound/",
        {"organization_id": str(org.id), "from": "+5491150000000", "body": "hola"},
        format="json",
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_inbound_runs_ai_and_returns_reply(api_client):
    org = OrganizationFactory()
    setup_ai_organization(org)
    res = api_client.post(
        "/api/v1/whatsapp/bridge/inbound/",
        {
            "organization_id": str(org.id),
            "from": "+5491150000000",
            "body": "Hola, quiero info de automatización",
            "message_id": "wamid.test.1",
        },
        format="json",
        **_secret_headers(),
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["mode"] == "sales_ai"
    assert data["should_send"] is True
    assert data["reply"]
    # Inbound + AI outbound both persisted in the conversation.
    assert Message.objects.filter(conversation_id=data["conversation_id"]).count() == 2


@pytest.mark.django_db
def test_owner_message_uses_personal_assistant(api_client, settings):
    org = OrganizationFactory()
    setup_ai_organization(org)
    settings.OWNER_WHATSAPP_NUMBER = "5491137725766"
    res = api_client.post(
        "/api/v1/whatsapp/bridge/inbound/",
        {
            "organization_id": str(org.id),
            "from": "+5491137725766",
            "body": "Resumime cómo viene el día",
        },
        format="json",
        **_secret_headers(),
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["mode"] == "internal_assistant"
    assert data["should_send"] is True
    assert data["reply"]


@pytest.mark.django_db
def test_owner_dictated_task_becomes_a_card(api_client, settings):
    from crm.tasks.domain.enums import TaskSourceType
    from crm.tasks.models import Task

    org = OrganizationFactory()
    setup_ai_organization(org)
    settings.OWNER_WHATSAPP_NUMBER = "5491137725766"
    res = api_client.post(
        "/api/v1/whatsapp/bridge/inbound/",
        {
            "organization_id": str(org.id),
            "from": "+5491137725766",
            "body": "Recordame llamar a Juan mañana a las 3",
            "message_id": "wamid.task.1",
        },
        format="json",
        **_secret_headers(),
    )
    assert res.status_code == 200
    assert res.json()["data"]["mode"] == "internal_assistant"
    # The owner's dictated task auto-confirms and lands as a card in Tareas.
    tasks = Task.objects.filter(organization_id=org.id)
    assert tasks.count() == 1
    assert tasks.first().source_type == TaskSourceType.AI_EXTRACTED.value


@pytest.mark.django_db
def test_owner_propuesta_command_generates_document(api_client, settings, tmp_path):
    settings.OWNER_WHATSAPP_NUMBER = "5491137725766"
    settings.MEDIA_PRIVATE_ROOT = str(tmp_path)
    org = OrganizationFactory()
    setup_ai_organization(org)
    res = api_client.post(
        "/api/v1/whatsapp/bridge/inbound/",
        {
            "organization_id": str(org.id),
            "from": "+5491137725766",
            "body": "/propuesta para ACME: app de turnos, backend + web, 3 meses de soporte",
        },
        format="json",
        **_secret_headers(),
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["mode"] == "internal_assistant"
    assert data["should_send"] is True
    assert data["reason"] == "document_generated"
    assert data["document"] is not None
    assert data["document"]["file_name"].endswith(".pdf")
    assert "token=" in data["document"]["url"]

    from crm.documents.models import GeneratedDocument

    doc = GeneratedDocument.objects.get(organization_id=org.id, doc_type="proposal")
    assert doc.doc_format == "pdf"
    assert doc.media_asset_id is not None


@pytest.mark.django_db
def test_owner_excel_command_generates_xlsx(api_client, settings, tmp_path):
    settings.OWNER_WHATSAPP_NUMBER = "5491137725766"
    settings.MEDIA_PRIVATE_ROOT = str(tmp_path)
    org = OrganizationFactory()
    setup_ai_organization(org)
    res = api_client.post(
        "/api/v1/whatsapp/bridge/inbound/",
        {
            "organization_id": str(org.id),
            "from": "+5491137725766",
            "body": "/excel presupuesto landing 800000 y hosting 50000 x12",
        },
        format="json",
        **_secret_headers(),
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["reason"] == "document_generated"
    assert data["document"]["file_name"].endswith(".xlsx")


@pytest.mark.django_db
def test_non_owner_propuesta_is_not_a_command(api_client, settings):
    # A regular lead writing "/propuesta ..." must NOT trigger document generation.
    settings.OWNER_WHATSAPP_NUMBER = "5491137725766"
    org = OrganizationFactory()
    setup_ai_organization(org)
    res = api_client.post(
        "/api/v1/whatsapp/bridge/inbound/",
        {
            "organization_id": str(org.id),
            "from": "+5491150000000",
            "body": "/propuesta quiero una propuesta",
        },
        format="json",
        **_secret_headers(),
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["mode"] == "sales_ai"
    assert data["document"] is None


@pytest.mark.django_db
def test_inbound_prospect_reply_is_interpreted(api_client):
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = ProspectingCampaign.objects.create(
        organization_id=org.id,
        name="Gomerias",
        vertical="gomerias",
        query="gomerias en Palermo",
        status=CampaignStatus.ACTIVE.value,
    )
    prospect = Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name="Gomeria Sur",
        place_id="place-1",
        phone="+5491155550000",
        status=ProspectStatus.APPROVED.value,
        fit_score=78,
        signals=["no_website"],
    )
    ProspectOutreachService.contact_prospect(prospect=prospect, jitter_seconds=0)

    res = api_client.post(
        "/api/v1/whatsapp/bridge/inbound/",
        {
            "organization_id": str(org.id),
            "from": "+5491155550000",
            "body": "Mandame info, me interesa.",
            "message_id": "wamid.prospect.reply",
        },
        format="json",
        **_secret_headers(),
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["prospect"]["intent"] == "interested"
    prospect.refresh_from_db()
    assert prospect.status == ProspectStatus.INTERESTED.value
    assert prospect.lead_id is not None


@pytest.mark.django_db
def test_inbound_without_ai_setup_is_graceful(api_client):
    org = OrganizationFactory()  # no AI provider/config configured
    res = api_client.post(
        "/api/v1/whatsapp/bridge/inbound/",
        {"organization_id": str(org.id), "from": "+5491150000001", "body": "hola"},
        format="json",
        **_secret_headers(),
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["should_send"] is False
    assert data["reply"] is None


@pytest.mark.django_db
def test_event_and_status_roundtrip(api_client):
    user = UserFactory()
    org = OrganizationFactory(owner=user)
    MembershipFactory(organization=org, user=user, role=Role.OWNER.value)

    posted = api_client.post(
        "/api/v1/whatsapp/bridge/event/",
        {"organization_id": str(org.id), "type": "qr", "qr": "data:image/png;base64,AAAA"},
        format="json",
        **_secret_headers(),
    )
    assert posted.status_code == 200

    api_client.force_authenticate(user=user)
    status = api_client.get(
        "/api/v1/whatsapp/bridge/status/",
        HTTP_X_ORGANIZATION_ID=str(org.id),
    )
    assert status.status_code == 200
    data = status.json()["data"]
    assert data["state"] == "qr"
    assert data["qr"] == "data:image/png;base64,AAAA"
