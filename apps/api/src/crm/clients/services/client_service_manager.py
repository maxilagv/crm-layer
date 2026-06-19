"""Manage the services a client has contracted (feeds support context)."""

from django.db import transaction

from crm.audit.services import audit_event_create
from crm.clients.domain.enums import ServiceStatus, ServiceType
from crm.clients.models import ClientService

from ._support import org_stub


class ClientServiceManager:
    @staticmethod
    @transaction.atomic
    def add_service(
        *,
        client,
        name: str,
        service_type: str = ServiceType.OTHER.value,
        status: str = ServiceStatus.ACTIVE.value,
        configuration: dict | None = None,
        actor=None,
        request=None,
    ) -> ClientService:
        service = ClientService.objects.create(
            organization_id=client.organization_id,
            client=client,
            name=name,
            service_type=service_type,
            status=status,
            configuration=configuration or {},
            created_by_id=getattr(actor, "id", None),
        )
        if actor is not None:
            audit_event_create(
                event_type="client_service_added",
                actor=actor,
                organization=org_stub(client.organization_id),
                request=request,
                resource_type="clients_client_service",
                resource_id=str(service.id),
                metadata={"client_id": str(client.id), "name": name},
            )
        return service
