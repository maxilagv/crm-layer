import factory

from crm.clients.domain.enums import ClientStatus, SupportLevel
from crm.clients.models import Client, ClientContact, ClientService
from tests.factories.contacts import ContactFactory


class ClientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Client

    contact = factory.SubFactory(ContactFactory)
    organization_id = factory.SelfAttribute("contact.organization_id")
    display_name = factory.Sequence(lambda n: f"Client {n}")
    status = ClientStatus.ACTIVE
    support_level = SupportLevel.STANDARD


class ClientContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ClientContact

    client = factory.SubFactory(ClientFactory)
    contact = factory.SelfAttribute("client.contact")
    organization_id = factory.SelfAttribute("client.organization_id")
    is_primary = True
    can_request_support = True


class ClientServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ClientService

    client = factory.SubFactory(ClientFactory)
    organization_id = factory.SelfAttribute("client.organization_id")
    name = factory.Sequence(lambda n: f"Service {n}")
