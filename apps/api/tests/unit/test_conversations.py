import pytest
from django.db import transaction

from crm.contacts.constants import ContactType
from crm.conversations.constants import (
    Channel,
    ConversationMode,
    ConversationStatus,
    MessageDirection,
    MessageStatus,
)
from crm.conversations.models import Message
from crm.conversations.services import (
    ConversationHandoffService,
    ConversationMemoryService,
    ConversationResolver,
    ConversationSummaryService,
    MessageIngestionService,
)
from crm.core.models import OutboxEvent
from tests.factories.accounts import UserFactory
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory
from tests.factories.organizations import OrganizationFactory

AR_LANDLINE = "+541143215678"


@pytest.mark.django_db
def test_conversation_created_for_contact():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id, type=ContactType.LEAD)
    result = ConversationResolver.resolve(
        organization=org, contact=contact, channel=Channel.WHATSAPP
    )
    assert result.created is True
    assert result.conversation.contact_id == contact.id
    assert result.conversation.mode == ConversationMode.SALES_AI.value
    assert OutboxEvent.objects.filter(
        event_type="conversation.created.v1", organization_id=org.id
    ).exists()


@pytest.mark.django_db
def test_resolver_reuses_open_conversation():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id, type=ContactType.LEAD)
    first = ConversationResolver.resolve(
        organization=org, contact=contact, channel=Channel.WHATSAPP
    )
    second = ConversationResolver.resolve(
        organization=org, contact=contact, channel=Channel.WHATSAPP
    )
    assert second.created is False
    assert second.conversation.id == first.conversation.id


@pytest.mark.django_db
def test_resolver_creates_new_per_channel():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id, type=ContactType.LEAD)
    wa = ConversationResolver.resolve(organization=org, contact=contact, channel=Channel.WHATSAPP)
    email = ConversationResolver.resolve(organization=org, contact=contact, channel=Channel.EMAIL)
    assert wa.conversation.id != email.conversation.id


@pytest.mark.django_db
def test_message_ingestion_inbound():
    org = OrganizationFactory()
    result = MessageIngestionService.ingest(
        organization=org,
        channel=Channel.WHATSAPP,
        direction=MessageDirection.INBOUND,
        phone=AR_LANDLINE,
        body="Hola, quiero informacion",
        external_message_id="wamid.001",
    )
    assert result.created_contact is True
    assert result.created_conversation is True
    assert result.deduplicated is False
    assert result.message.direction == MessageDirection.INBOUND.value
    assert result.message.status == MessageStatus.RECEIVED.value
    assert result.message.normalized_text == "hola, quiero informacion"

    result.conversation.refresh_from_db()
    assert result.conversation.last_message_at is not None
    assert result.conversation.last_inbound_at is not None
    assert result.conversation.last_outbound_at is None
    assert OutboxEvent.objects.filter(
        event_type="conversation.message_received.v1", organization_id=org.id
    ).exists()


@pytest.mark.django_db
def test_message_external_id_deduplication():
    org = OrganizationFactory()
    first = MessageIngestionService.ingest(
        organization=org,
        channel=Channel.WHATSAPP,
        direction=MessageDirection.INBOUND,
        phone=AR_LANDLINE,
        body="Hola",
        external_message_id="wamid.dup",
    )
    second = MessageIngestionService.ingest(
        organization=org,
        channel=Channel.WHATSAPP,
        direction=MessageDirection.INBOUND,
        phone=AR_LANDLINE,
        body="Hola again",
        external_message_id="wamid.dup",
    )
    assert second.deduplicated is True
    assert second.message.id == first.message.id
    assert (
        Message.objects.filter(organization_id=org.id, external_message_id="wamid.dup").count() == 1
    )


@pytest.mark.django_db
def test_outbound_updates_last_outbound_at():
    org = OrganizationFactory()
    conversation = ConversationFactory(organization_id=org.id)
    result = MessageIngestionService.ingest(
        organization=org,
        conversation=conversation,
        contact=conversation.contact,
        channel=conversation.channel,
        direction=MessageDirection.OUTBOUND,
        body="Gracias por escribirnos",
    )
    assert result.message.direction == MessageDirection.OUTBOUND.value
    assert result.message.status == MessageStatus.QUEUED.value
    conversation.refresh_from_db()
    assert conversation.last_outbound_at is not None
    assert OutboxEvent.objects.filter(
        event_type="conversation.message_sent.v1", organization_id=org.id
    ).exists()


@pytest.mark.django_db
def test_ingestion_events_are_atomic_with_message():
    org = OrganizationFactory()
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            MessageIngestionService.ingest(
                organization=org,
                channel=Channel.WHATSAPP,
                direction=MessageDirection.INBOUND,
                phone=AR_LANDLINE,
                body="Hola",
                external_message_id="wamid.rollback",
            )
            raise RuntimeError("boom")
    assert Message.objects.count() == 0
    assert OutboxEvent.objects.filter(event_type="conversation.message_received.v1").count() == 0


@pytest.mark.django_db
def test_pause_ai():
    conversation = ConversationFactory(mode=ConversationMode.SALES_AI, ai_enabled=True)
    actor = UserFactory()
    ConversationHandoffService.pause_ai(conversation=conversation, actor=actor)
    conversation.refresh_from_db()
    assert conversation.ai_enabled is False
    assert conversation.mode == ConversationMode.PAUSED.value
    assert OutboxEvent.objects.filter(event_type="conversation.mode_changed.v1").exists()


@pytest.mark.django_db
def test_resume_ai_recomputes_mode():
    contact = ContactFactory(type=ContactType.LEAD)
    conversation = ConversationFactory(
        contact=contact, mode=ConversationMode.PAUSED, ai_enabled=False
    )
    actor = UserFactory()
    ConversationHandoffService.resume_ai(conversation=conversation, actor=actor)
    conversation.refresh_from_db()
    assert conversation.ai_enabled is True
    assert conversation.mode == ConversationMode.SALES_AI.value


@pytest.mark.django_db
def test_takeover_sets_manual_mode():
    conversation = ConversationFactory(mode=ConversationMode.SALES_AI, ai_enabled=True)
    actor = UserFactory()
    ConversationHandoffService.takeover(conversation=conversation, actor=actor)
    conversation.refresh_from_db()
    assert conversation.mode == ConversationMode.MANUAL.value
    assert conversation.ai_enabled is False
    assert conversation.assigned_user_id == actor.id


@pytest.mark.django_db
def test_close_and_reopen():
    contact = ContactFactory(type=ContactType.CLIENT)
    conversation = ConversationFactory(contact=contact, status=ConversationStatus.OPEN)
    actor = UserFactory()

    ConversationHandoffService.close(conversation=conversation, actor=actor)
    conversation.refresh_from_db()
    assert conversation.status == ConversationStatus.CLOSED.value

    ConversationHandoffService.reopen(conversation=conversation, actor=actor)
    conversation.refresh_from_db()
    assert conversation.status == ConversationStatus.OPEN.value
    assert conversation.mode == ConversationMode.SUPPORT_AI.value


@pytest.mark.django_db
def test_summary_and_memory_services():
    conversation = ConversationFactory()
    summary = ConversationSummaryService.create(conversation=conversation, summary="Resumen breve")
    assert summary.conversation_id == conversation.id

    memory = ConversationMemoryService.create(
        conversation=conversation,
        memory_type="preference",
        content="Prefiere mañanas",
        importance=4,
    )
    assert memory.importance == 4
    assert memory.contact_id == conversation.contact_id

    with pytest.raises(ValueError):
        ConversationMemoryService.create(
            conversation=conversation, memory_type="preference", content="x", importance=9
        )
