"""Pull-based WhatsApp bridge outbound queue."""

import pytest
from django.utils import timezone

from crm.contacts.models import Contact
from crm.conversations.constants import MessageStatus
from crm.conversations.models import Conversation, Message
from crm.whatsapp.domain.enums import BridgeOutboundStatus
from crm.whatsapp.models import OutboundMessage
from crm.whatsapp.services.outbound_queue import WhatsAppOutboundQueueService
from tests.factories.organizations import OrganizationFactory


@pytest.mark.django_db
def test_enqueue_creates_contact_conversation_message_and_queue_row():
    org = OrganizationFactory()

    result = WhatsAppOutboundQueueService.enqueue(
        organization=org,
        phone="+5491155550000",
        body="Hola, soy Martin.",
        idempotency_key="prospect-1-opener",
    )

    assert result.created is True
    assert result.outbound.status == BridgeOutboundStatus.PENDING.value
    assert result.outbound.contact_phone == "+5491155550000"
    assert Contact.objects.filter(organization_id=org.id, source="prospecting").count() == 1
    assert Conversation.objects.filter(organization_id=org.id).count() == 1
    message = Message.objects.get(organization_id=org.id)
    assert message.status == MessageStatus.QUEUED.value
    assert result.outbound.metadata["crm_message_id"] == str(message.id)


@pytest.mark.django_db
def test_enqueue_is_idempotent_by_key():
    org = OrganizationFactory()

    first = WhatsAppOutboundQueueService.enqueue(
        organization=org,
        phone="+5491155550000",
        body="Hola uno",
        idempotency_key="same-key",
    )
    second = WhatsAppOutboundQueueService.enqueue(
        organization=org,
        phone="+5491155550000",
        body="Hola dos",
        idempotency_key="same-key",
    )

    assert first.created is True
    assert second.created is False
    assert second.outbound.id == first.outbound.id
    assert OutboundMessage.objects.filter(organization_id=org.id).count() == 1
    assert Message.objects.filter(organization_id=org.id).count() == 1


@pytest.mark.django_db
def test_claim_pending_marks_processing():
    org = OrganizationFactory()
    queued = WhatsAppOutboundQueueService.enqueue(
        organization=org,
        phone="+5491155550000",
        body="Hola",
        idempotency_key="claim-me",
    ).outbound

    rows = WhatsAppOutboundQueueService.claim_pending(organization=org, limit=10)

    assert [row.id for row in rows] == [queued.id]
    queued.refresh_from_db()
    assert queued.status == BridgeOutboundStatus.PROCESSING.value
    assert WhatsAppOutboundQueueService.claim_pending(organization=org, limit=10) == []


@pytest.mark.django_db
def test_delivery_status_sent_updates_queue_and_message():
    org = OrganizationFactory()
    outbound = WhatsAppOutboundQueueService.enqueue(
        organization=org,
        phone="+5491155550000",
        body="Hola",
        idempotency_key="sent-key",
    ).outbound

    updated = WhatsAppOutboundQueueService.record_delivery_status(
        organization=org,
        message_id=outbound.id,
        status="sent",
    )

    assert updated.status == BridgeOutboundStatus.SENT.value
    assert updated.sent_at is not None
    message = Message.objects.get(id=outbound.metadata["crm_message_id"])
    assert message.status == MessageStatus.SENT.value


@pytest.mark.django_db
def test_delivery_status_failed_retries_with_backoff_then_dead_letter():
    org = OrganizationFactory()
    outbound = WhatsAppOutboundQueueService.enqueue(
        organization=org,
        phone="+5491155550000",
        body="Hola",
        idempotency_key="retry-key",
    ).outbound

    first = WhatsAppOutboundQueueService.record_delivery_status(
        organization=org,
        message_id=outbound.id,
        status="failed",
        reason="unregistered_number",
    )

    assert first.status == BridgeOutboundStatus.PENDING.value
    assert first.attempts == 1
    assert first.error_reason == "unregistered_number"
    assert first.available_at > timezone.now()

    OutboundMessage.objects.filter(id=outbound.id).update(
        attempts=4,
        status=BridgeOutboundStatus.PROCESSING.value,
        available_at=timezone.now(),
    )
    dead = WhatsAppOutboundQueueService.record_delivery_status(
        organization=org,
        message_id=outbound.id,
        status="failed",
        reason="unregistered_number",
    )

    assert dead.status == BridgeOutboundStatus.DEAD_LETTER.value
    assert dead.attempts == 5
    message = Message.objects.get(id=outbound.metadata["crm_message_id"])
    assert message.status == MessageStatus.FAILED.value
