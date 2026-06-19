"""ClientRegistrationService: create a Client around an existing Contact.

Reuses the contact (so a lead converted in Phase 6 is NOT duplicated), sets
``Contact.type = client``, creates a primary ClientContact and the initial
status-history row. Idempotent: an existing active client for the contact is
returned instead of raising (unless ``raise_on_duplicate``).
"""

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from crm.audit.services import audit_event_create
from crm.clients.domain import events
from crm.clients.domain.enums import (
    ChangedByType,
    ClientContactRole,
    ClientStatus,
    SupportLevel,
)
from crm.clients.domain.exceptions import DuplicateActiveClient
from crm.clients.models import Client, ClientContact, ClientStatusHistory
from crm.contacts.constants import ContactType
from crm.core.services.outbox import create_outbox_event

from ._support import org_stub


@dataclass(frozen=True)
class ClientRegistrationResult:
    client: Client
    created: bool


class ClientRegistrationService:
    @staticmethod
    @transaction.atomic
    def register(
        *,
        organization,
        contact,
        display_name: str = "",
        service_plan: str = "",
        support_level: str = SupportLevel.STANDARD.value,
        company=None,
        actor=None,
        request=None,
        raise_on_duplicate: bool = False,
    ) -> ClientRegistrationResult:
        existing = (
            Client.objects.filter(
                organization_id=organization.id,
                contact=contact,
                status=ClientStatus.ACTIVE,
            )
            .order_by("-created_at")
            .first()
        )
        if existing is not None:
            if raise_on_duplicate:
                raise DuplicateActiveClient()
            return ClientRegistrationResult(client=existing, created=False)

        # Reuse the contact; mark it as a client so routing sends it to support.
        if contact.type != ContactType.CLIENT:
            contact.type = ContactType.CLIENT
            contact.save(update_fields=["type", "updated_at"])

        if company is None:
            primary_link = (
                contact.company_links.filter(is_primary=True).select_related("company").first()
            )
            company = primary_link.company if primary_link else None

        client = Client.objects.create(
            organization_id=organization.id,
            contact=contact,
            company=company,
            display_name=display_name or contact.display_name,
            status=ClientStatus.ACTIVE,
            service_plan=service_plan,
            support_level=support_level,
            started_at=timezone.now(),
            created_by_id=getattr(actor, "id", None),
        )
        ClientContact.objects.create(
            organization_id=organization.id,
            client=client,
            contact=contact,
            role=ClientContactRole.OWNER,
            is_primary=True,
            can_request_support=True,
            receives_notifications=True,
            created_by_id=getattr(actor, "id", None),
        )
        ClientStatusHistory.objects.create(
            organization_id=organization.id,
            client=client,
            from_status="",
            to_status=ClientStatus.ACTIVE.value,
            reason="client_registered",
            changed_by_id=getattr(actor, "id", None),
            changed_by_type=ChangedByType.USER.value if actor else ChangedByType.SYSTEM.value,
        )
        create_outbox_event(
            event_type=events.CLIENT_CREATED,
            organization_id=organization.id,
            payload={
                "event_type": events.CLIENT_CREATED,
                "organization_id": str(organization.id),
                "data": {"client_id": str(client.id), "contact_id": str(contact.id)},
                "metadata": {"request_id": getattr(request, "request_id", None)},
            },
        )
        if actor is not None:
            audit_event_create(
                event_type="client_created",
                actor=actor,
                organization=org_stub(organization.id),
                request=request,
                resource_type="clients_client",
                resource_id=str(client.id),
                metadata={"contact_id": str(contact.id)},
            )
        return ClientRegistrationResult(client=client, created=True)
