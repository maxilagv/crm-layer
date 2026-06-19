"""Manage the contacts attached to a client (primary, support permissions)."""

from django.db import IntegrityError, transaction

from crm.audit.services import audit_event_create
from crm.clients.domain import events
from crm.clients.domain.enums import ClientContactRole
from crm.clients.domain.exceptions import DuplicateClientContact
from crm.clients.models import ClientContact
from crm.core.services.outbox import create_outbox_event

from ._support import org_stub


class ClientContactService:
    @staticmethod
    @transaction.atomic
    def add_contact(
        *,
        client,
        contact,
        role: str = ClientContactRole.USER.value,
        is_primary: bool = False,
        can_request_support: bool = True,
        receives_notifications: bool = False,
        actor=None,
        request=None,
    ) -> ClientContact:
        try:
            link = ClientContact.objects.create(
                organization_id=client.organization_id,
                client=client,
                contact=contact,
                role=role,
                is_primary=is_primary,
                can_request_support=can_request_support,
                receives_notifications=receives_notifications,
                created_by_id=getattr(actor, "id", None),
            )
        except IntegrityError as exc:
            raise DuplicateClientContact() from exc

        if is_primary:
            ClientContact.objects.filter(client=client, is_primary=True).exclude(id=link.id).update(
                is_primary=False
            )

        create_outbox_event(
            event_type=events.CLIENT_CONTACT_ADDED,
            organization_id=client.organization_id,
            payload={
                "event_type": events.CLIENT_CONTACT_ADDED,
                "organization_id": str(client.organization_id),
                "data": {"client_id": str(client.id), "contact_id": str(contact.id), "role": role},
                "metadata": {"request_id": getattr(request, "request_id", None)},
            },
        )
        if actor is not None:
            audit_event_create(
                event_type="client_contact_added",
                actor=actor,
                organization=org_stub(client.organization_id),
                request=request,
                resource_type="clients_client_contact",
                resource_id=str(link.id),
                metadata={"client_id": str(client.id), "contact_id": str(contact.id)},
            )
        return link
