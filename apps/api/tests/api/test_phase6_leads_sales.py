import ast
from pathlib import Path

import pytest

from crm.ai.providers.fake_provider import FakeAIProvider
from crm.contacts.constants import ContactStatus, ContactType
from crm.conversations.constants import ConversationMode
from crm.core.models import OutboxEvent
from crm.core.security.permissions import Role
from crm.leads.domain.enums import LeadStage, LeadStatus
from crm.leads.models import Lead, LeadScoreSnapshot, LeadStageHistory
from crm.leads.services.lead_conversion import convert_to_client
from crm.leads.services.lead_creation import create_or_get_lead_from_conversation
from crm.leads.services.lead_lifecycle import change_stage
from crm.leads.services.lead_qualification import detect_unqualified_from_text
from crm.leads.services.lead_scoring import score_lead
from crm.sales.domain.enums import ObjectionType
from crm.sales.domain.events import SALES_HOT_LEAD_OWNER_NOTIFICATION, SALES_REPLY_READY
from crm.sales.models import SalesCallRequest, SalesFollowup, SalesObjection, SalesOpportunity
from crm.sales.services.followup_service import create_followup
from crm.sales.services.sales_call_closer import create_call_request
from crm.sales.services.sales_conversation_agent import (
    SalesConversationAgent,
    notify_owner_for_hot_lead,
)
from tests.factories.accounts import UserFactory
from tests.factories.ai import setup_ai_organization
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory, MessageFactory
from tests.factories.leads import LeadFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory


@pytest.fixture(autouse=True)
def _reset_fake_provider():
    FakeAIProvider.reset()
    yield
    FakeAIProvider.reset()


def _member(role: Role = Role.OPERATOR):
    user = UserFactory()
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=role.value)
    return user, organization


def _auth(api_client, user, organization):
    api_client.force_authenticate(user=user)
    return {"HTTP_X_ORGANIZATION_ID": str(organization.id)}


def _conversation(organization, *, contact_type=ContactType.UNKNOWN, body=None):
    contact = ContactFactory(organization_id=organization.id, type=contact_type)
    conversation = ConversationFactory(
        organization_id=organization.id,
        contact=contact,
        mode=ConversationMode.SALES_AI,
        ai_enabled=True,
    )
    message = MessageFactory(
        conversation=conversation,
        body=body or "Tengo un problema urgente con ventas por WhatsApp y quiero automatizar.",
    )
    return contact, conversation, message


def _valid_sales_output(**overrides):
    payload = {
        "reply": "Para entender bien el caso, ¿cuantos leads reciben por WhatsApp por semana?",
        "intent": "qualify_lead",
        "lead_updates": {},
        "suggested_tasks": [],
        "should_notify_owner": False,
        "should_handoff": False,
        "should_create_call_request": False,
        "risk_level": "low",
        "confidence": 0.9,
    }
    payload.update(overrides)
    return payload


def _valid_lead_score_output(**overrides):
    payload = {
        "score": 100,
        "temperature": "hot",
        "pain_points": [],
        "urgency": "low",
        "budget_signal": "none",
        "authority_signal": "unknown",
        "business_fit": "low",
        "technical_match": "low",
        "risk_penalty": 0,
        "next_best_action": "ask_diagnostic_question",
        "confidence": 0.8,
        "reasoning_summary": "Salida IA valida pero el backend recalcula score.",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_unknown_contact_becomes_lead():
    _user, organization = _member()
    contact, conversation, message = _conversation(organization)

    result = create_or_get_lead_from_conversation(
        organization=organization,
        conversation=conversation,
        message=message,
    )

    assert result.created is True
    assert result.lead.contact_id == contact.id
    contact.refresh_from_db()
    assert contact.type == ContactType.LEAD
    assert LeadStageHistory.objects.filter(lead=result.lead, to_stage=LeadStage.NEW).exists()
    assert result.lead.sources.first().source_type == "whatsapp"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "contact_type", [ContactType.CLIENT, ContactType.INTERNAL, ContactType.BLOCKED]
)
def test_disallowed_contacts_do_not_become_leads(contact_type):
    _user, organization = _member()
    contact, conversation, message = _conversation(organization, contact_type=contact_type)
    if contact_type == ContactType.BLOCKED:
        contact.status = ContactStatus.BLOCKED
        contact.save(update_fields=["status", "updated_at"])

    result = create_or_get_lead_from_conversation(
        organization=organization,
        conversation=conversation,
        message=message,
    )

    assert result.lead is None
    assert Lead.objects.filter(organization_id=organization.id, contact=contact).count() == 0


@pytest.mark.django_db
def test_lead_score_calculation_uses_backend_weights_not_ai_score_directly():
    _user, organization = _member()
    setup_ai_organization(organization)
    contact, conversation, message = _conversation(organization, contact_type=ContactType.LEAD)
    lead = LeadFactory(organization_id=organization.id, contact=contact)

    result = score_lead(
        lead=lead,
        conversation=conversation,
        metadata={"fake_output": _valid_lead_score_output(score=100)},
    )

    lead.refresh_from_db()
    assert result.updated is True
    assert lead.score != 100
    assert lead.score == result.snapshot.score
    assert LeadScoreSnapshot.objects.filter(lead=lead).count() == 1
    assert result.snapshot.ai_run_id is not None
    assert message.body


@pytest.mark.django_db
def test_invalid_ai_output_does_not_update_lead():
    _user, organization = _member()
    setup_ai_organization(organization)
    contact, conversation, _message = _conversation(organization, contact_type=ContactType.LEAD)
    lead = LeadFactory(organization_id=organization.id, contact=contact, score=10)

    result = score_lead(
        lead=lead,
        conversation=conversation,
        metadata={"fake_behavior": "invalid_schema"},
    )

    lead.refresh_from_db()
    assert result.updated is False
    assert lead.score == 10
    assert LeadScoreSnapshot.objects.filter(lead=lead).count() == 0


@pytest.mark.django_db
def test_hot_lead_triggers_notification_once():
    _user, organization = _member()
    lead = LeadFactory(organization_id=organization.id, score=82)

    assert notify_owner_for_hot_lead(lead=lead, reason="test") is True
    assert notify_owner_for_hot_lead(lead=lead, reason="test") is False

    assert (
        OutboxEvent.objects.filter(
            organization_id=organization.id,
            event_type=SALES_HOT_LEAD_OWNER_NOTIFICATION,
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_sales_agent_does_not_invent_price():
    _user, organization = _member()
    setup_ai_organization(organization)
    _contact, conversation, message = _conversation(
        organization,
        body="Cuanto sale? Me interesa pero quiero saber precio.",
    )

    result = SalesConversationAgent.generate_reply(
        organization=organization,
        conversation=conversation,
        message=message,
        ai_metadata={
            "fake_output": _valid_sales_output(reply="Sale USD 100 y te garantizo resultados.")
        },
    )

    assert result.blocked is True
    assert (
        "precio" in " ".join(result.reasons).lower() or "garant" in " ".join(result.reasons).lower()
    )
    assert OutboxEvent.objects.filter(event_type=SALES_REPLY_READY).count() == 0


@pytest.mark.django_db
def test_sales_agent_asks_diagnostic_question():
    _user, organization = _member()
    setup_ai_organization(organization)
    _contact, conversation, message = _conversation(organization)

    result = SalesConversationAgent.generate_reply(
        organization=organization,
        conversation=conversation,
        message=message,
        ai_metadata={"fake_output": _valid_sales_output()},
    )

    assert result.blocked is False
    assert "?" in result.reply or "¿" in result.reply
    assert OutboxEvent.objects.filter(event_type=SALES_REPLY_READY).count() == 1


@pytest.mark.django_db
def test_sales_agent_creates_call_request():
    _user, organization = _member()
    setup_ai_organization(organization)
    _contact, conversation, message = _conversation(organization)

    result = SalesConversationAgent.generate_reply(
        organization=organization,
        conversation=conversation,
        message=message,
        ai_metadata={
            "fake_output": _valid_sales_output(
                intent="propose_call",
                should_create_call_request=True,
                reply="Tiene sentido verlo en llamada. ¿Coordinamos una breve?",
            )
        },
    )

    assert result.blocked is False
    assert SalesCallRequest.objects.filter(lead=result.lead).count() == 1
    result.lead.refresh_from_db()
    assert result.lead.stage == LeadStage.CALL_REQUESTED


@pytest.mark.django_db
def test_objection_price_handling():
    _user, organization = _member()
    setup_ai_organization(organization)
    _contact, conversation, message = _conversation(
        organization,
        body="Me parece muy caro para lo que necesito.",
    )

    result = SalesConversationAgent.generate_reply(
        organization=organization,
        conversation=conversation,
        message=message,
        ai_metadata={
            "fake_output": _valid_sales_output(
                intent="handle_objection",
                reply="Entiendo la objecion de precio. Primero validemos alcance y valor.",
            )
        },
    )

    assert result.blocked is False
    objection = SalesObjection.objects.get(lead=result.lead)
    assert objection.objection_type == ObjectionType.PRICE


@pytest.mark.django_db
def test_lead_stage_history_created():
    _user, organization = _member()
    lead = LeadFactory(organization_id=organization.id)

    change_stage(lead=lead, to_stage=LeadStage.WARM, reason="manual")
    change_stage(lead=lead, to_stage=LeadStage.WARM, reason="same")

    assert LeadStageHistory.objects.filter(lead=lead, to_stage=LeadStage.WARM).count() == 1


@pytest.mark.django_db
def test_lead_convert_to_client():
    _user, organization = _member()
    contact = ContactFactory(organization_id=organization.id, type=ContactType.LEAD)
    lead = LeadFactory(organization_id=organization.id, contact=contact)

    converted = convert_to_client(lead=lead, reason="closed")
    contact.refresh_from_db()
    converted.refresh_from_db()

    assert contact.type == ContactType.CLIENT
    assert converted.status == LeadStatus.WON
    assert converted.stage == LeadStage.WON
    assert SalesOpportunity.objects.filter(lead=lead).exists()


@pytest.mark.django_db
def test_unqualified_lead_detection():
    _user, organization = _member()
    lead = LeadFactory(organization_id=organization.id)

    updated = detect_unqualified_from_text(lead=lead, text="No me interesa, gracias.")

    assert updated is not None
    updated.refresh_from_db()
    assert updated.status == LeadStatus.UNQUALIFIED
    assert updated.stage == LeadStage.UNQUALIFIED


@pytest.mark.django_db
def test_call_request_and_followup_are_idempotent():
    _user, organization = _member()
    lead = LeadFactory(organization_id=organization.id)

    first_call, first_created = create_call_request(lead=lead)
    second_call, second_created = create_call_request(lead=lead)
    assert first_created is True
    assert second_created is False
    assert first_call.id == second_call.id

    first_followup, first_followup_created = create_followup(
        lead=lead,
        due_at=first_call.requested_at,
        title="Seguimiento",
        idempotency_key="same-key",
    )
    second_followup, second_followup_created = create_followup(
        lead=lead,
        due_at=first_call.requested_at,
        title="Seguimiento",
        idempotency_key="same-key",
    )
    assert first_followup_created is True
    assert second_followup_created is False
    assert first_followup.id == second_followup.id
    assert SalesFollowup.objects.filter(lead=lead).count() == 1


@pytest.mark.django_db
def test_leads_api_filters_and_cross_organization_isolation(api_client):
    user, organization = _member(Role.OPERATOR)
    _other_user, other_org = _member(Role.OWNER)
    LeadFactory(organization_id=organization.id, stage=LeadStage.HOT, score=80)
    LeadFactory(organization_id=organization.id, stage=LeadStage.WARM, score=60)
    LeadFactory(organization_id=other_org.id, stage=LeadStage.HOT, score=90)

    response = api_client.get(
        "/api/v1/leads/?stage=hot",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 200
    assert response.json()["pagination"]["total"] == 1
    assert response.json()["data"][0]["stage"] == "hot"


@pytest.mark.django_db
def test_lead_score_endpoint(api_client):
    user, organization = _member(Role.OPERATOR)
    contact, conversation, _message = _conversation(organization, contact_type=ContactType.LEAD)
    lead = LeadFactory(organization_id=organization.id, contact=contact)

    response = api_client.post(
        f"/api/v1/leads/{lead.id}/score/",
        {"conversation_id": str(conversation.id), "use_ai": False},
        format="json",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 200
    assert response.json()["data"]["score"] >= 0


@pytest.mark.django_db
def test_sales_opportunities_crud_and_call_request_schedule_endpoint(api_client):
    user, organization = _member(Role.OPERATOR)
    lead = LeadFactory(organization_id=organization.id)
    headers = _auth(api_client, user, organization)

    created = api_client.post(
        "/api/v1/sales/opportunities/",
        {"lead_id": str(lead.id), "title": "CRM operativo", "probability": 40},
        format="json",
        **headers,
    )
    assert created.status_code == 201
    listed = api_client.get("/api/v1/sales/opportunities/", **headers)
    assert listed.json()["pagination"]["total"] == 1

    call_request, _created = create_call_request(lead=lead)
    scheduled = api_client.post(
        f"/api/v1/sales/call-requests/{call_request.id}/mark-scheduled/",
        {"scheduled_at": "2026-06-20T15:00:00Z", "notes": "Agenda confirmada"},
        format="json",
        **headers,
    )
    assert scheduled.status_code == 200
    assert scheduled.json()["data"]["status"] == "scheduled"


def test_sales_and_leads_do_not_import_openai_or_anthropic():
    root = Path(__file__).resolve().parents[2] / "src" / "crm"
    offenders = []
    for path in [*(root / "leads").rglob("*.py"), *(root / "sales").rglob("*.py")]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in {"openai", "anthropic"}:
                        offenders.append(str(path))
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in {
                "openai",
                "anthropic",
            }:
                offenders.append(str(path))
    assert offenders == []
