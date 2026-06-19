"""Cazador 14.5: outreach orchestration and reply interpretation."""

import pytest

from crm.ai.providers.fake_provider import FakeAIProvider
from crm.contacts.constants import ContactStatus
from crm.conversations.constants import Channel, MessageDirection, MessageStatus, MessageType
from crm.conversations.services import MessageIngestionService
from crm.leads.models import Lead
from crm.notifications.models import Notification
from crm.prospecting.domain.enums import CampaignStatus, ProspectStatus
from crm.prospecting.models import Prospect, ProspectingCampaign
from crm.prospecting.services.outreach import ProspectOutreachService
from crm.prospecting.services.replies import ProspectReplyInterpreter
from crm.whatsapp.models import OutboundMessage
from tests.factories.ai import setup_ai_organization
from tests.factories.organizations import OrganizationFactory


@pytest.fixture(autouse=True)
def _reset_fake_provider():
    FakeAIProvider.reset()
    yield
    FakeAIProvider.reset()


def _campaign(org, **kwargs):
    defaults = {
        "organization_id": org.id,
        "name": "Gomerias Palermo",
        "vertical": "gomerias",
        "query": "gomerias en Palermo",
        "target_profile": "Sin web y con baja madurez digital.",
        "status": CampaignStatus.ACTIVE.value,
        "daily_cap": 10,
    }
    defaults.update(kwargs)
    return ProspectingCampaign.objects.create(**defaults)


def _prospect(org, campaign, **kwargs):
    defaults = {
        "organization_id": org.id,
        "campaign": campaign,
        "business_name": "Gomeria Sur",
        "place_id": "place-1",
        "phone": "+5491155550000",
        "status": ProspectStatus.APPROVED.value,
        "fit_score": 78,
        "signals": ["no_website"],
        "recommended_angle": "Turnos por WhatsApp.",
    }
    defaults.update(kwargs)
    return Prospect.objects.create(**defaults)


@pytest.mark.django_db
def test_outreach_contacts_approved_prospect_and_updates_links():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org)
    prospect = _prospect(org, campaign)

    result = ProspectOutreachService.contact_prospect(prospect=prospect, jitter_seconds=0)

    assert result.queued is True
    updated = result.prospect
    assert updated.status == ProspectStatus.CONTACTED.value
    assert updated.contacted_at is not None
    assert updated.contact_id is not None
    assert updated.conversation_id is not None
    assert OutboundMessage.objects.filter(prospect_id=prospect.id).count() == 1
    campaign.refresh_from_db()
    assert campaign.contacted_count == 1


@pytest.mark.django_db
def test_outreach_honors_paused_campaign_daily_cap_and_dedup():
    org = OrganizationFactory()
    setup_ai_organization(org)
    paused = _campaign(org, status=CampaignStatus.PAUSED.value)
    paused_prospect = _prospect(org, paused)
    assert (
        ProspectOutreachService.contact_prospect(prospect=paused_prospect).reason
        == "campaign_not_active"
    )

    capped = _campaign(org, name="Cap", daily_cap=1)
    first = _prospect(org, capped, place_id="p1", phone="+5491155550001")
    second = _prospect(org, capped, place_id="p2", phone="+5491155550002")
    assert ProspectOutreachService.contact_prospect(prospect=first).queued is True
    assert ProspectOutreachService.contact_prospect(prospect=first).reason == "already_contacted"
    assert ProspectOutreachService.contact_prospect(prospect=second).reason == "daily_cap_reached"


@pytest.mark.django_db
def test_outreach_auto_contacts_qualified_when_campaign_allows_it():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org, auto_contact=True, min_fit_score=70)
    prospect = _prospect(
        org,
        campaign,
        status=ProspectStatus.QUALIFIED.value,
        fit_score=78,
    )

    attempts = ProspectOutreachService.run_campaign(campaign=campaign)

    assert len(attempts) == 1
    assert attempts[0].queued is True
    prospect.refresh_from_db()
    assert prospect.status == ProspectStatus.CONTACTED.value


@pytest.mark.django_db
def test_reply_interpreter_promotes_interested_prospect_to_lead_and_notifies_owner():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org)
    prospect = _prospect(org, campaign)
    contacted = ProspectOutreachService.contact_prospect(prospect=prospect).prospect
    inbound = MessageIngestionService.ingest(
        organization=org,
        channel=Channel.WHATSAPP,
        direction=MessageDirection.INBOUND,
        contact=None,
        phone="+5491155550000",
        conversation=None,
        message_type=MessageType.TEXT,
        body="Mandame info, me interesa.",
        status=MessageStatus.RECEIVED,
    )

    result = ProspectReplyInterpreter.interpret_inbound(
        organization=org,
        conversation=inbound.conversation,
        contact=inbound.contact,
        message=inbound.message,
    )

    assert result is not None
    assert result.intent == "interested"
    contacted.refresh_from_db()
    assert contacted.status == ProspectStatus.INTERESTED.value
    assert contacted.lead_id is not None
    assert Lead.objects.filter(organization_id=org.id, id=contacted.lead_id).exists()
    assert Notification.objects.filter(
        organization_id=org.id,
        resource_type="prospecting_prospect",
        resource_id=contacted.id,
    ).exists()
    campaign.refresh_from_db()
    assert campaign.interested_count == 1


@pytest.mark.django_db
def test_reply_interpreter_honors_opt_out_without_ai_call():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org)
    prospect = _prospect(org, campaign)
    contacted = ProspectOutreachService.contact_prospect(prospect=prospect).prospect
    inbound = MessageIngestionService.ingest(
        organization=org,
        channel=Channel.WHATSAPP,
        direction=MessageDirection.INBOUND,
        phone="+5491155550000",
        message_type=MessageType.TEXT,
        body="No me escriban mas",
    )

    result = ProspectReplyInterpreter.interpret_inbound(
        organization=org,
        conversation=inbound.conversation,
        contact=inbound.contact,
        message=inbound.message,
    )

    assert result is not None
    assert result.intent == "do_not_contact"
    assert result.opted_out is True
    contacted.refresh_from_db()
    assert contacted.status == ProspectStatus.DO_NOT_CONTACT.value
    inbound.contact.refresh_from_db()
    assert inbound.contact.status == ContactStatus.BLOCKED.value
    assert Lead.objects.filter(organization_id=org.id).count() == 0
