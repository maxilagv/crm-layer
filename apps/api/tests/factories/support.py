import uuid

import factory

from crm.support.domain.enums import TicketCategory, TicketPriority, TicketStatus
from crm.support.models import SupportKnownIssue, SupportTicket
from tests.factories.contacts import ContactFactory


class SupportTicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SupportTicket

    contact = factory.SubFactory(ContactFactory)
    organization_id = factory.SelfAttribute("contact.organization_id")
    title = factory.Sequence(lambda n: f"Ticket {n}")
    description = "El cliente reporta un problema."
    status = TicketStatus.OPEN
    priority = TicketPriority.MEDIUM
    category = TicketCategory.BUG


class SupportKnownIssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SupportKnownIssue

    organization_id = factory.LazyFunction(uuid.uuid4)
    title = factory.Sequence(lambda n: f"Known issue {n}")
    category = TicketCategory.INTEGRATION
    matching_keywords = factory.List(["whatsapp", "integracion"])
