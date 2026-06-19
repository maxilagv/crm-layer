"""ClientResolver: decide whether a contact/phone is an active client.

A registered client must route to support, not sales. ``Contact.type == client``
(set at registration) already makes ConversationRouter return ``support_ai``;
this resolver adds the explicit, organization-scoped client lookup used by the
support context and routing checks.
"""

from crm.clients.domain.policies import status_is_support_routable
from crm.clients.domain.rules import contact_blocks_support
from crm.clients.domain.value_objects import ClientResolution
from crm.clients.models import Client, ClientContact
from crm.contacts.models import Contact, ContactPhone


class ClientResolver:
    @staticmethod
    def resolve_by_contact(contact_id, organization_id) -> ClientResolution:
        contact = Contact.objects.filter(organization_id=organization_id, id=contact_id).first()
        if contact is None:
            return ClientResolution.negative("contact_not_found")
        if contact_blocks_support(contact):
            return ClientResolution.negative("blocked_contact", contact_id=contact_id)

        # Primary: the contact owns a routable client.
        client = (
            Client.objects.filter(organization_id=organization_id, contact_id=contact_id)
            .order_by("-created_at")
            .first()
        )
        if client is not None and status_is_support_routable(client.status):
            return ClientResolution(
                is_client=True,
                reason="active_client_contact",
                client_id=client.id,
                contact_id=contact_id,
                support_level=client.support_level,
                can_request_support=True,
            )

        # Secondary: the contact is an authorized member of someone's client.
        link = (
            ClientContact.objects.filter(
                organization_id=organization_id,
                contact_id=contact_id,
                can_request_support=True,
            )
            .select_related("client")
            .order_by("-created_at")
            .first()
        )
        if link is not None and status_is_support_routable(link.client.status):
            return ClientResolution(
                is_client=True,
                reason="authorized_client_contact",
                client_id=link.client_id,
                contact_id=contact_id,
                support_level=link.client.support_level,
                can_request_support=True,
            )

        if client is not None or link is not None:
            return ClientResolution.negative("inactive_client", contact_id=contact_id)
        return ClientResolution.negative("not_a_client", contact_id=contact_id)

    @staticmethod
    def resolve_by_phone(phone_e164, organization_id) -> ClientResolution:
        phone = (
            ContactPhone.objects.filter(organization_id=organization_id, phone_e164=phone_e164)
            .order_by("-is_primary")
            .first()
        )
        if phone is None:
            return ClientResolution.negative("phone_not_found")
        return ClientResolver.resolve_by_contact(phone.contact_id, organization_id)

    @staticmethod
    def is_client_contact(contact_id, organization_id) -> bool:
        return ClientResolver.resolve_by_contact(contact_id, organization_id).is_client

    @staticmethod
    def get_support_context(contact_id, organization_id, conversation_id=None) -> dict:
        resolution = ClientResolver.resolve_by_contact(contact_id, organization_id)
        context = resolution.as_dict()
        context["conversation_id"] = str(conversation_id) if conversation_id else None
        if resolution.client_id:
            services = list(
                Client.objects.get(id=resolution.client_id)
                .services.filter(status="active")
                .values("name", "service_type", "status")
            )
            context["services"] = services
        return context
