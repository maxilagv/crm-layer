"""Cazador conversation engine: autonomous replies and follow-ups."""

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from crm.ai.models import AIRun
from crm.ai.providers.fake_provider import FakeAIProvider
from crm.contacts.constants import ContactStatus
from crm.conversations.constants import Channel, MessageDirection, MessageStatus, MessageType
from crm.conversations.services import MessageIngestionService
from crm.notifications.models import Notification
from crm.prospecting.domain.enums import CampaignStatus, ProspectStatus
from crm.prospecting.models import Prospect, ProspectingCampaign
from crm.prospecting.services.outreach import ProspectOutreachService
from crm.prospecting.services.replies import ProspectReplyInterpreter
from crm.prospecting.tasks import run_followups
from crm.whatsapp.models import OutboundMessage
from tests.factories.ai import setup_ai_organization
from tests.factories.organizations import OrganizationFactory


@pytest.fixture(autouse=True)
def _reset_state():
    FakeAIProvider.reset()
    cache.clear()
    yield
    FakeAIProvider.reset()
    cache.clear()


def _campaign(org, **kwargs):
    defaults = {
        "organization_id": org.id,
        "name": "Gomerias Palermo",
        "vertical": "gomerias",
        "query": "gomerias en Palermo",
        "target_profile": "Sin web y con baja madurez digital.",
        "status": CampaignStatus.ACTIVE.value,
        "daily_cap": 10,
        "max_touches": 3,
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


def _contacted_prospect(org, campaign):
    prospect = _prospect(org, campaign)
    return ProspectOutreachService.contact_prospect(prospect=prospect, jitter_seconds=0).prospect


def _inbound(org, body: str, phone: str = "+5491155550000"):
    return MessageIngestionService.ingest(
        organization=org,
        channel=Channel.WHATSAPP,
        direction=MessageDirection.INBOUND,
        phone=phone,
        message_type=MessageType.TEXT,
        body=body,
        status=MessageStatus.RECEIVED,
    )


def _classification(next_action="rebut_objection", intent="maybe", objection_type="precio"):
    return {
        "intent": intent,
        "confidence": 0.91,
        "reasoning": "Respuesta clasificada por test.",
        "next_action": next_action,
        "objection_type": objection_type,
    }


def _draft(message="Si, tiene sentido. Te muestro una version simple y lo ves sin compromiso?"):
    return {
        "message": message,
        "should_send": True,
        "handoff": False,
        "reason": "Borrador seguro para avanzar un micro-paso.",
    }


@pytest.mark.django_db
def test_inbound_rebut_objection_auto_reply_enqueues_once_and_updates_touch_count():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org, auto_reply=True)
    prospect = _contacted_prospect(org, campaign)
    inbound = _inbound(org, "Me interesa, pero me preocupa el precio.")
    FakeAIProvider.script({"json": _classification()}, {"json": _draft("Te muestro algo simple?")})

    result = ProspectReplyInterpreter.interpret_inbound(
        organization=org,
        conversation=inbound.conversation,
        contact=inbound.contact,
        message=inbound.message,
    )

    assert result is not None
    assert result.response_queued is True
    assert (
        OutboundMessage.objects.filter(organization_id=org.id, prospect_id=prospect.id).count() == 2
    )
    prospect.refresh_from_db()
    assert prospect.touch_count == 2
    assert prospect.last_touch_at is not None
    assert str(inbound.message.id) in prospect.metadata["prospecting_interpreted_message_ids"]

    again = ProspectReplyInterpreter.interpret_inbound(
        organization=org,
        conversation=inbound.conversation,
        contact=inbound.contact,
        message=inbound.message,
    )
    assert again is not None
    assert again.response_queued is False
    assert (
        OutboundMessage.objects.filter(organization_id=org.id, prospect_id=prospect.id).count() == 2
    )


@pytest.mark.django_db
def test_auto_reply_false_notifies_owner_with_draft_without_enqueueing():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org, auto_reply=False)
    prospect = _contacted_prospect(org, campaign)
    inbound = _inbound(org, "Mandame mas info.")
    FakeAIProvider.script(
        {"json": _classification(next_action="send_info", intent="interested", objection_type="")},
        {"json": _draft("Te paso la idea por aca y si te sirve coordinamos 10 min.")},
    )

    result = ProspectReplyInterpreter.interpret_inbound(
        organization=org,
        conversation=inbound.conversation,
        contact=inbound.contact,
        message=inbound.message,
    )

    assert result is not None
    assert result.owner_notified is True
    assert (
        OutboundMessage.objects.filter(organization_id=org.id, prospect_id=prospect.id).count() == 1
    )
    notification = Notification.objects.filter(
        organization_id=org.id,
        resource_type="prospecting_prospect",
        resource_id=prospect.id,
        metadata__mode="reply",
    ).latest("created_at")
    assert notification.metadata["suggested_reply"].startswith("Te paso la idea")


@pytest.mark.django_db
def test_opt_out_cuts_reply_generation_and_queueing():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org, auto_reply=True)
    prospect = _contacted_prospect(org, campaign)
    before_runs = AIRun.objects.filter(organization_id=org.id).count()
    inbound = _inbound(org, "No me escriban mas")

    result = ProspectReplyInterpreter.interpret_inbound(
        organization=org,
        conversation=inbound.conversation,
        contact=inbound.contact,
        message=inbound.message,
    )

    assert result is not None
    assert result.opted_out is True
    prospect.refresh_from_db()
    assert prospect.status == ProspectStatus.DO_NOT_CONTACT.value
    inbound.contact.refresh_from_db()
    assert inbound.contact.status == ContactStatus.BLOCKED.value
    assert (
        OutboundMessage.objects.filter(organization_id=org.id, prospect_id=prospect.id).count() == 1
    )
    assert AIRun.objects.filter(organization_id=org.id).count() == before_runs


@pytest.mark.django_db
def test_handoff_draft_notifies_owner_without_sending():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org, auto_reply=True)
    prospect = _contacted_prospect(org, campaign)
    inbound = _inbound(org, "Esto lo tiene que aprobar mi socio con contrato.")
    FakeAIProvider.script(
        {"json": _classification(next_action="rebut_objection", intent="maybe")},
        {
            "json": {
                "message": "Prefiero que lo vea Martin y te conteste bien.",
                "should_send": False,
                "handoff": True,
                "reason": "Requiere decision humana.",
            }
        },
    )

    result = ProspectReplyInterpreter.interpret_inbound(
        organization=org,
        conversation=inbound.conversation,
        contact=inbound.contact,
        message=inbound.message,
    )

    assert result is not None
    assert result.owner_notified is True
    assert (
        OutboundMessage.objects.filter(organization_id=org.id, prospect_id=prospect.id).count() == 1
    )
    assert Notification.objects.filter(
        organization_id=org.id,
        resource_id=prospect.id,
        metadata__safety__decision="handoff_to_human",
    ).exists()


@pytest.mark.django_db
def test_daily_cap_blocks_autonomous_reply_and_notifies_owner():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org, auto_reply=True, daily_cap=1)
    prospect = _contacted_prospect(org, campaign)
    inbound = _inbound(org, "Dale, contame.")
    FakeAIProvider.script(
        {"json": _classification(next_action="send_info", intent="interested", objection_type="")},
        {"json": _draft("Te paso una idea concreta para verlo rapido.")},
    )

    result = ProspectReplyInterpreter.interpret_inbound(
        organization=org,
        conversation=inbound.conversation,
        contact=inbound.contact,
        message=inbound.message,
    )

    assert result is not None
    assert result.owner_notified is True
    assert (
        OutboundMessage.objects.filter(organization_id=org.id, prospect_id=prospect.id).count() == 1
    )
    assert Notification.objects.filter(
        organization_id=org.id,
        resource_id=prospect.id,
        metadata__reason="daily_cap_reached",
    ).exists()


@pytest.mark.django_db
def test_followup_task_selects_due_prospect_enqueues_and_reprograms():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org, auto_followup=True)
    prospect = _contacted_prospect(org, campaign)
    due_at = timezone.now() - timedelta(hours=1)
    Prospect.objects.filter(id=prospect.id).update(
        status=ProspectStatus.CONTACTED.value,
        touch_count=1,
        follow_up_count=0,
        last_touch_at=timezone.now() - timedelta(days=4),
        next_followup_at=due_at,
    )
    FakeAIProvider.script({"json": _draft("Te dejo el ejemplo por aca y lo ves cuando puedas.")})

    queued = run_followups(limit=10)

    assert queued == 1
    prospect.refresh_from_db()
    assert prospect.follow_up_count == 1
    assert prospect.touch_count == 2
    assert prospect.next_followup_at is not None
    assert prospect.next_followup_at > timezone.now() + timedelta(days=6)
    assert (
        OutboundMessage.objects.filter(organization_id=org.id, prospect_id=prospect.id).count() == 2
    )


@pytest.mark.django_db
def test_followup_task_stops_at_max_touches():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org, auto_followup=True, max_touches=2)
    prospect = _contacted_prospect(org, campaign)
    Prospect.objects.filter(id=prospect.id).update(
        touch_count=2,
        next_followup_at=timezone.now() - timedelta(hours=1),
    )

    assert run_followups(limit=10) == 0
    assert (
        OutboundMessage.objects.filter(organization_id=org.id, prospect_id=prospect.id).count() == 1
    )


@pytest.mark.django_db
def test_followup_task_honors_campaign_kill_switches():
    org = OrganizationFactory()
    setup_ai_organization(org)
    inactive = _campaign(
        org, name="Inactive", auto_followup=True, status=CampaignStatus.PAUSED.value
    )
    disabled = _campaign(org, name="Disabled", auto_followup=False)
    p1 = _contacted_prospect(org, inactive)
    p2 = _prospect(org, disabled, place_id="p2", phone="+5491155550002")
    p2.status = ProspectStatus.CONTACTED.value
    p2.contacted_at = timezone.now() - timedelta(days=5)
    p2.last_touch_at = timezone.now() - timedelta(days=5)
    p2.touch_count = 1
    p2.next_followup_at = timezone.now() - timedelta(hours=1)
    p2.save()
    Prospect.objects.filter(id=p1.id).update(next_followup_at=timezone.now() - timedelta(hours=1))

    assert run_followups(limit=10) == 0
    assert OutboundMessage.objects.filter(organization_id=org.id).count() == 0
