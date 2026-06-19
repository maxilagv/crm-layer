import factory

from crm.leads.domain.enums import LeadStage, LeadStatus, LeadTemperature
from crm.leads.models import Lead, LeadScoreSnapshot, LeadSource, LeadStageHistory
from tests.factories.contacts import ContactFactory


class LeadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lead

    contact = factory.SubFactory(ContactFactory)
    organization_id = factory.SelfAttribute("contact.organization_id")
    status = LeadStatus.ACTIVE
    stage = LeadStage.NEW
    score = 0
    temperature = LeadTemperature.COLD


class LeadScoreSnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeadScoreSnapshot

    lead = factory.SubFactory(LeadFactory)
    organization_id = factory.SelfAttribute("lead.organization_id")
    score = 42
    temperature = LeadTemperature.WARM
    reasoning_summary = "Snapshot"
    factors = {
        "pain_clear": 10,
        "urgency": 5,
        "authority": 5,
        "budget_signal": 3,
        "business_fit": 10,
        "engagement": 5,
        "technical_match": 4,
        "risk_penalty": 0,
    }


class LeadStageHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeadStageHistory

    lead = factory.SubFactory(LeadFactory)
    organization_id = factory.SelfAttribute("lead.organization_id")
    from_stage = ""
    to_stage = LeadStage.NEW
    reason = "created"


class LeadSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeadSource

    lead = factory.SubFactory(LeadFactory)
    organization_id = factory.SelfAttribute("lead.organization_id")
    source_type = "manual"
