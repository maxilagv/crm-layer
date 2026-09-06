import pytest
from django.core.cache import cache

from crm.ai.services.context_builder import ContextBuilder
from crm.prospecting.domain.enums import CampaignStatus, ProspectStatus
from crm.prospecting.models import Prospect, ProspectingCampaign
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory, MessageFactory
from tests.factories.organizations import OrganizationFactory


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _conversation_message(org, body: str = "cuantos prospectos tenemos?"):
    contact = ContactFactory(organization_id=org.id)
    conversation = ConversationFactory(contact=contact)
    message = MessageFactory(conversation=conversation, body=body)
    return conversation, message


def _campaign(org, name: str = "Gomerias Palermo"):
    return ProspectingCampaign.objects.create(
        organization_id=org.id,
        name=name,
        vertical="gomerias",
        query="gomerias en Palermo",
        target_profile="Sin web y con baja madurez digital.",
        status=CampaignStatus.ACTIVE.value,
    )


def _prospect(org, campaign, *, status: str, place_id: str):
    return Prospect.objects.create(
        organization_id=org.id,
        campaign=campaign,
        business_name=f"Gomeria {place_id}",
        place_id=place_id,
        phone=f"+549115555{place_id[-4:]}",
        status=status,
    )


@pytest.mark.django_db
def test_assistant_context_includes_prospecting_stats_for_current_org():
    org = OrganizationFactory()
    other_org = OrganizationFactory()
    campaign = _campaign(org)
    other_campaign = _campaign(other_org, name="Otra campana")
    statuses = [
        ProspectStatus.QUALIFIED.value,
        ProspectStatus.QUALIFIED.value,
        ProspectStatus.APPROVED.value,
        ProspectStatus.CONTACTED.value,
        ProspectStatus.CONTACTED.value,
        ProspectStatus.CONTACTED.value,
        ProspectStatus.REPLIED.value,
        ProspectStatus.INTERESTED.value,
    ]
    for index, status in enumerate(statuses, start=1):
        _prospect(org, campaign, status=status, place_id=f"place-{index}")
    for index in range(5):
        _prospect(
            other_org,
            other_campaign,
            status=ProspectStatus.INTERESTED.value,
            place_id=f"other-{index}",
        )

    conversation, message = _conversation_message(org)

    context = ContextBuilder.for_assistant_reply(
        conversation=conversation,
        current_message=message,
    )

    stats = context["prospecting_stats"]
    assert "8 total" in stats
    assert "2 calificados" in stats
    assert "1 aprobados" in stats
    assert "3 contactados" in stats
    assert "1 respondieron" in stats
    assert "1 interesados" in stats
    assert "13 total" not in stats


@pytest.mark.django_db
def test_assistant_context_reports_empty_prospecting_stats():
    org = OrganizationFactory()
    conversation, message = _conversation_message(org)

    context = ContextBuilder.for_assistant_reply(
        conversation=conversation,
        current_message=message,
    )

    assert context["prospecting_stats"] == "Todavía no hay prospectos cargados."
