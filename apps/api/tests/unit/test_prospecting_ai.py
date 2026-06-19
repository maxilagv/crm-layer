"""Cazador 14.3: AI qualification, outreach opener and reply intent."""

import pytest

from crm.ai.domain.enums import AIPurpose
from crm.ai.providers.fake_provider import FakeAIProvider
from crm.ai.schemas import schema_for_purpose
from crm.ai.schemas.outreach_opener import OutreachOpenerSchema
from crm.ai.schemas.outreach_reply import OutreachReplySchema
from crm.ai.schemas.prospect_qualification import ProspectQualificationSchema
from crm.ai.schemas.reply_intent import ReplyIntentSchema
from crm.ai.services.ai_gateway import AIGateway
from crm.prospecting.models import Prospect, ProspectingCampaign
from crm.prospecting.services.qualification import ProspectQualificationService
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
        "target_profile": "Sin web, pocas fotos y bajo volumen de reviews.",
        "min_fit_score": 60,
    }
    defaults.update(kwargs)
    return ProspectingCampaign.objects.create(**defaults)


def _prospect(org, campaign, **kwargs):
    defaults = {
        "organization_id": org.id,
        "campaign": campaign,
        "business_name": "Gomeria Sur",
        "place_id": "places-1",
        "category": "car_repair",
        "address": "Av Siempre Viva 123",
        "phone": "+5491155550000",
        "reviews_count": 8,
        "photos_count": 1,
    }
    defaults.update(kwargs)
    return Prospect.objects.create(**defaults)


def test_prospecting_schemas_registered_and_examples_valid():
    assert schema_for_purpose(AIPurpose.PROSPECT_QUALIFICATION.value) is ProspectQualificationSchema
    assert schema_for_purpose(AIPurpose.OUTREACH_OPENER.value) is OutreachOpenerSchema
    assert schema_for_purpose(AIPurpose.OUTREACH_REPLY.value) is OutreachReplySchema
    assert schema_for_purpose(AIPurpose.REPLY_INTENT.value) is ReplyIntentSchema
    ProspectQualificationSchema.model_validate(ProspectQualificationSchema.example)
    OutreachOpenerSchema.model_validate(OutreachOpenerSchema.example)
    OutreachReplySchema.model_validate(OutreachReplySchema.example)
    ReplyIntentSchema.model_validate(ReplyIntentSchema.example)


@pytest.mark.django_db
def test_gateway_runs_cazador_structured_purposes():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org)
    prospect = _prospect(org, campaign)

    qualification = AIGateway.qualify_prospect(prospect_id=prospect.id)
    opener = AIGateway.draft_outreach_opener(prospect_id=prospect.id)
    outreach_reply = AIGateway.draft_prospect_reply(
        prospect_id=prospect.id,
        mode="reply",
        intent="maybe",
        next_action="rebut_objection",
        objection_type="precio",
    )
    reply = AIGateway.classify_prospect_reply(prospect_id=prospect.id)

    assert qualification.succeeded
    assert qualification.purpose == AIPurpose.PROSPECT_QUALIFICATION.value
    assert qualification.data["fit_score"] == 78
    assert opener.succeeded
    assert opener.purpose == AIPurpose.OUTREACH_OPENER.value
    assert opener.data["message"]
    assert outreach_reply.succeeded
    assert outreach_reply.purpose == AIPurpose.OUTREACH_REPLY.value
    assert outreach_reply.data["message"]
    assert outreach_reply.data["should_send"] is True
    assert reply.succeeded
    assert reply.purpose == AIPurpose.REPLY_INTENT.value
    assert reply.data["intent"] == "interested"


@pytest.mark.django_db
def test_qualification_service_persists_verdict_and_counter():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org, min_fit_score=70)
    prospect = _prospect(org, campaign)

    updated = ProspectQualificationService.qualify(prospect=prospect)

    assert updated.status == "qualified"
    assert updated.fit_score == 78
    assert updated.qualified_at is not None
    assert updated.ai_run_id is not None
    assert updated.signals == ["no_website", "few_photos", "strong_reviews"]
    campaign.refresh_from_db()
    assert campaign.qualified_count == 1


@pytest.mark.django_db
def test_qualification_service_disqualifies_below_campaign_threshold():
    org = OrganizationFactory()
    setup_ai_organization(org)
    campaign = _campaign(org, min_fit_score=90)
    prospect = _prospect(org, campaign)

    updated = ProspectQualificationService.qualify(prospect=prospect)

    assert updated.status == "disqualified"
    assert updated.fit_score == 78
    campaign.refresh_from_db()
    assert campaign.qualified_count == 0
