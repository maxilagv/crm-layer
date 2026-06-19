"""Bridge outbox pull endpoints."""

import pytest

from crm.whatsapp.domain.enums import BridgeOutboundStatus
from crm.whatsapp.models import OutboundMessage
from crm.whatsapp.services.outbound_queue import WhatsAppOutboundQueueService
from tests.factories.organizations import OrganizationFactory

SECRET = "s3cret-bridge"


@pytest.fixture(autouse=True)
def _bridge_secret(settings):
    settings.WA_BRIDGE_SHARED_SECRET = SECRET


def _secret_headers():
    return {"HTTP_X_BRIDGE_SECRET": SECRET}


@pytest.mark.django_db
def test_outbox_requires_secret(api_client):
    org = OrganizationFactory()
    res = api_client.get(
        "/api/v1/whatsapp/bridge/outbox/",
        {"organization_id": str(org.id)},
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_outbox_returns_pending_and_marks_processing(api_client):
    org = OrganizationFactory()
    outbound = WhatsAppOutboundQueueService.enqueue(
        organization=org,
        phone="+5491155550000",
        body="Hola desde Cazador",
        idempotency_key="outbox-key",
    ).outbound

    res = api_client.get(
        "/api/v1/whatsapp/bridge/outbox/",
        {"organization_id": str(org.id)},
        **_secret_headers(),
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data == [
        {
            "id": str(outbound.id),
            "phone": "+5491155550000",
            "body": "Hola desde Cazador",
            "idempotency_key": "outbox-key",
        }
    ]
    outbound.refresh_from_db()
    assert outbound.status == BridgeOutboundStatus.PROCESSING.value


@pytest.mark.django_db
def test_delivery_status_endpoint_records_sent_and_failed(api_client):
    org = OrganizationFactory()
    sent = WhatsAppOutboundQueueService.enqueue(
        organization=org,
        phone="+5491155550000",
        body="Hola",
        idempotency_key="status-sent",
    ).outbound
    failed = WhatsAppOutboundQueueService.enqueue(
        organization=org,
        phone="+5491155550001",
        body="Hola",
        idempotency_key="status-failed",
    ).outbound

    sent_res = api_client.post(
        "/api/v1/whatsapp/bridge/delivery-status/",
        {"organization_id": str(org.id), "message_id": str(sent.id), "status": "sent"},
        format="json",
        **_secret_headers(),
    )
    failed_res = api_client.post(
        "/api/v1/whatsapp/bridge/delivery-status/",
        {
            "organization_id": str(org.id),
            "message_id": str(failed.id),
            "status": "failed",
            "reason": "unregistered_number",
        },
        format="json",
        **_secret_headers(),
    )

    assert sent_res.status_code == 200
    assert sent_res.json()["data"]["status"] == BridgeOutboundStatus.SENT.value
    assert failed_res.status_code == 200
    assert failed_res.json()["data"]["status"] == BridgeOutboundStatus.PENDING.value
    assert OutboundMessage.objects.get(id=failed.id).attempts == 1
