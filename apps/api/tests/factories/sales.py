import uuid

import factory
from django.utils import timezone

from crm.sales.domain.enums import CallRequestStatus, FollowupStatus, OpportunityStage
from crm.sales.models import (
    SalesCallRequest,
    SalesFollowup,
    SalesObjection,
    SalesOpportunity,
    SalesPlaybook,
)
from tests.factories.leads import LeadFactory


class SalesOpportunityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesOpportunity

    lead = factory.SubFactory(LeadFactory)
    contact = factory.SelfAttribute("lead.contact")
    organization_id = factory.SelfAttribute("lead.organization_id")
    title = factory.Sequence(lambda n: f"Opportunity {n}")
    stage = OpportunityStage.NEW
    probability = 10


class SalesFollowupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesFollowup

    lead = factory.SubFactory(LeadFactory)
    contact = factory.SelfAttribute("lead.contact")
    organization_id = factory.SelfAttribute("lead.organization_id")
    title = "Seguimiento comercial"
    status = FollowupStatus.PENDING
    due_at = factory.LazyFunction(timezone.now)
    idempotency_key = factory.Sequence(lambda n: f"followup-{n}")


class SalesObjectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesObjection

    lead = factory.SubFactory(LeadFactory)
    contact = factory.SelfAttribute("lead.contact")
    organization_id = factory.SelfAttribute("lead.organization_id")
    objection_type = "price"
    summary = "Objecion de precio"


class SalesPlaybookFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesPlaybook

    organization_id = factory.LazyFunction(uuid.uuid4)
    key = factory.Sequence(lambda n: f"playbook-{n}")
    name = factory.Sequence(lambda n: f"Playbook {n}")


class SalesCallRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SalesCallRequest

    lead = factory.SubFactory(LeadFactory)
    contact = factory.SelfAttribute("lead.contact")
    organization_id = factory.SelfAttribute("lead.organization_id")
    status = CallRequestStatus.REQUESTED
    requested_at = factory.LazyFunction(timezone.now)
