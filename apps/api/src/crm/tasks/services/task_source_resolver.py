from dataclasses import dataclass

from crm.clients.models import Client
from crm.contacts.models import Contact
from crm.conversations.models import Conversation, Message
from crm.leads.models import Lead
from crm.support.models import SupportTicket


@dataclass(frozen=True)
class ResolvedTaskSource:
    contact: Contact | None = None
    lead: Lead | None = None
    client: Client | None = None
    ticket: SupportTicket | None = None
    conversation: Conversation | None = None
    source_message: Message | None = None


class TaskSourceResolver:
    @staticmethod
    def resolve(
        *,
        organization,
        contact_id=None,
        lead_id=None,
        client_id=None,
        ticket_id=None,
        conversation_id=None,
        source_message_id=None,
    ) -> ResolvedTaskSource:
        contact = _get(Contact, organization, contact_id)
        lead = _get(Lead, organization, lead_id)
        client = _get(Client, organization, client_id)
        ticket = _get(SupportTicket, organization, ticket_id)
        conversation = _get(Conversation, organization, conversation_id)
        source_message = _get(Message, organization, source_message_id)
        if source_message and not conversation:
            conversation = source_message.conversation
        if conversation and not contact:
            contact = conversation.contact
        if lead and not contact:
            contact = lead.contact
        if client and not contact:
            contact = client.contact
        if ticket and not contact:
            contact = ticket.contact
        return ResolvedTaskSource(
            contact=contact,
            lead=lead,
            client=client,
            ticket=ticket,
            conversation=conversation,
            source_message=source_message,
        )


def _get(model, organization, object_id):
    if not object_id:
        return None
    return model.objects.filter(id=object_id, organization_id=organization.id).first()
