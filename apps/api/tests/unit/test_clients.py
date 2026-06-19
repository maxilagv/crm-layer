import pytest

from crm.clients.domain.enums import ClientStatus, SupportLevel
from crm.clients.domain.exceptions import DuplicateActiveClient
from crm.clients.models import Client, ClientStatusHistory
from crm.clients.services.client_lifecycle import change_status
from crm.clients.services.client_registration import ClientRegistrationService
from crm.clients.services.client_resolver import ClientResolver
from crm.contacts.constants import ContactStatus, ContactType
from crm.conversations.constants import ConversationMode
from crm.conversations.router import route
from crm.core.models import OutboxEvent
from tests.factories.clients import ClientContactFactory, ClientFactory
from tests.factories.contacts import ContactFactory
from tests.factories.organizations import OrganizationFactory

AR_LANDLINE = "+541143215678"


@pytest.mark.django_db
def test_client_created_for_contact():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id)
    result = ClientRegistrationService.register(organization=org, contact=contact, actor=None)
    assert result.created is True
    contact.refresh_from_db()
    assert contact.type == ContactType.CLIENT
    assert result.client.client_contacts.filter(is_primary=True).count() == 1
    assert ClientStatusHistory.objects.filter(client=result.client).count() == 1
    assert OutboxEvent.objects.filter(
        event_type="client.created.v1", organization_id=org.id
    ).exists()


@pytest.mark.django_db
def test_client_unique_active_per_contact():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id)
    ClientRegistrationService.register(organization=org, contact=contact)
    # Idempotent reuse by default.
    again = ClientRegistrationService.register(organization=org, contact=contact)
    assert again.created is False
    # Explicit raise when requested.
    with pytest.raises(DuplicateActiveClient):
        ClientRegistrationService.register(
            organization=org, contact=contact, raise_on_duplicate=True
        )
    assert Client.objects.filter(organization_id=org.id, contact=contact).count() == 1


@pytest.mark.django_db
def test_lead_converted_client_reuses_contact():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id, type=ContactType.LEAD)
    result = ClientRegistrationService.register(organization=org, contact=contact)
    # Same contact reused, not duplicated.
    assert result.client.contact_id == contact.id
    assert ContactFactory._meta.model.objects.filter(id=contact.id).count() == 1


@pytest.mark.django_db
def test_registered_contact_routes_to_support():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id, type=ContactType.LEAD)
    ClientRegistrationService.register(organization=org, contact=contact)
    contact.refresh_from_db()
    # The router sends a client contact to support, not sales.
    assert route(contact) == ConversationMode.SUPPORT_AI.value
    # And the resolver agrees.
    assert ClientResolver.is_client_contact(contact.id, org.id) is True


@pytest.mark.django_db
def test_resolve_client_by_contact_and_phone():
    org = OrganizationFactory()
    from crm.contacts.services import create_contact

    contact = create_contact(
        organization=org, actor=None, type=ContactType.CLIENT, phones=[{"phone": AR_LANDLINE}]
    )
    ClientFactory(organization_id=org.id, contact=contact, support_level=SupportLevel.VIP)
    ClientContactFactory(client=Client.objects.get(contact=contact), contact=contact)

    by_contact = ClientResolver.resolve_by_contact(contact.id, org.id)
    assert by_contact.is_client is True
    assert by_contact.support_level == SupportLevel.VIP.value
    assert by_contact.reason == "active_client_contact"

    by_phone = ClientResolver.resolve_by_phone(AR_LANDLINE, org.id)
    assert by_phone.is_client is True
    assert by_phone.client_id == by_contact.client_id


@pytest.mark.django_db
def test_resolver_rejects_blocked_contact():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id, status=ContactStatus.BLOCKED)
    ClientFactory(organization_id=org.id, contact=contact)
    result = ClientResolver.resolve_by_contact(contact.id, org.id)
    assert result.is_client is False
    assert result.reason == "blocked_contact"


@pytest.mark.django_db
def test_resolver_respects_can_request_support():
    org = OrganizationFactory()
    owner_contact = ContactFactory(organization_id=org.id, type=ContactType.CLIENT)
    client = ClientFactory(organization_id=org.id, contact=owner_contact)
    member = ContactFactory(organization_id=org.id)
    ClientContactFactory(client=client, contact=member, is_primary=False, can_request_support=False)
    result = ClientResolver.resolve_by_contact(member.id, org.id)
    assert result.is_client is False


@pytest.mark.django_db
def test_cancelled_client_does_not_auto_route_to_support():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id, type=ContactType.CLIENT)
    ClientFactory(organization_id=org.id, contact=contact, status=ClientStatus.CANCELLED)
    result = ClientResolver.resolve_by_contact(contact.id, org.id)
    assert result.is_client is False
    assert result.reason == "inactive_client"


@pytest.mark.django_db
def test_resolver_is_organization_scoped():
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    contact = ContactFactory(organization_id=org_a.id, type=ContactType.CLIENT)
    ClientFactory(organization_id=org_a.id, contact=contact)
    assert ClientResolver.resolve_by_contact(contact.id, org_b.id).is_client is False


@pytest.mark.django_db
def test_client_status_change_creates_history():
    org = OrganizationFactory()
    client = ClientFactory(organization_id=org.id)
    change_status(client=client, to_status=ClientStatus.PAUSED.value, reason="vacaciones")
    client.refresh_from_db()
    assert client.status == ClientStatus.PAUSED.value
    assert ClientStatusHistory.objects.filter(
        client=client, to_status=ClientStatus.PAUSED.value
    ).exists()
    assert OutboxEvent.objects.filter(event_type="client.status_changed.v1").exists()
