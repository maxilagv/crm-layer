"""Client status transitions, each recorded in ClientStatusHistory + audited."""

from django.db import transaction
from django.utils import timezone

from crm.audit.services import audit_event_create
from crm.clients.domain import events
from crm.clients.domain.enums import ChangedByType, ClientStatus
from crm.clients.models import Client, ClientStatusHistory
from crm.core.services.outbox import create_outbox_event

from ._support import org_stub

_TERMINAL = {ClientStatus.CANCELLED.value, ClientStatus.ARCHIVED.value}


@transaction.atomic
def change_status(
    *,
    client: Client,
    to_status: str,
    reason: str = "",
    actor=None,
    changed_by_type: str = ChangedByType.USER.value,
    request=None,
) -> Client:
    if client.status == to_status:
        return client
    from_status = client.status
    client.status = to_status
    if to_status in _TERMINAL and client.ended_at is None:
        client.ended_at = timezone.now()
    if to_status == ClientStatus.ACTIVE.value and client.started_at is None:
        client.started_at = timezone.now()
    client.updated_by_id = getattr(actor, "id", None)
    client.save(update_fields=["status", "ended_at", "started_at", "updated_by_id", "updated_at"])

    ClientStatusHistory.objects.create(
        organization_id=client.organization_id,
        client=client,
        from_status=from_status,
        to_status=to_status,
        reason=reason[:255],
        changed_by_id=getattr(actor, "id", None),
        changed_by_type=changed_by_type,
    )
    create_outbox_event(
        event_type=events.CLIENT_STATUS_CHANGED,
        organization_id=client.organization_id,
        payload={
            "event_type": events.CLIENT_STATUS_CHANGED,
            "organization_id": str(client.organization_id),
            "data": {
                "client_id": str(client.id),
                "from_status": from_status,
                "to_status": to_status,
            },
            "metadata": {"request_id": getattr(request, "request_id", None)},
        },
    )
    audit_event_create(
        event_type="client_status_changed",
        actor=actor,
        organization=org_stub(client.organization_id),
        request=request,
        resource_type="clients_client",
        resource_id=str(client.id),
        changes={"status": {"before": from_status, "after": to_status}},
    )
    return client
