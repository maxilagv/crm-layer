"""Phase 9: long-term memory (9.1), owner voice (9.2), project briefs (9.4)."""

import pytest

from crm.ai.schemas import schema_for_purpose
from crm.ai.schemas.memory_extraction import MemoryExtractionSchema
from crm.ai.schemas.project_brief import ProjectBriefSchema
from crm.ai.services.ai_gateway import AIGateway
from crm.ai.services.context_builder import ContextBuilder
from crm.business_settings.models import BusinessProfile
from crm.conversations.constants import Channel, MessageDirection, MessageType
from crm.conversations.services import ConversationMemoryService, MessageIngestionService
from tests.factories.ai import setup_ai_organization
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory, MessageFactory
from tests.factories.organizations import OrganizationFactory


def test_phase9_schemas_registered_and_examples_valid():
    assert schema_for_purpose("memory_extraction") is MemoryExtractionSchema
    assert schema_for_purpose("project_brief") is ProjectBriefSchema
    # Examples must validate against their own schemas (FakeProvider returns them).
    MemoryExtractionSchema.model_validate(MemoryExtractionSchema.example)
    ProjectBriefSchema.model_validate(ProjectBriefSchema.example)


@pytest.mark.django_db
def test_owner_voice_uses_profile_fields():
    organization = OrganizationFactory()
    BusinessProfile.objects.create(
        organization_id=organization.id,
        owner_writing_style="Directo y cálido, sin vueltas.",
        signature_phrases=["dale", "te tiro la posta"],
    )
    voice = ContextBuilder._owner_voice(organization.id)["owner_voice"]
    assert "Directo y cálido" in voice
    assert "dale" in voice


@pytest.mark.django_db
def test_owner_voice_falls_back_when_unset():
    organization = OrganizationFactory()
    voice = ContextBuilder._owner_voice(organization.id)["owner_voice"]
    assert voice  # a sensible neutral default, never empty


@pytest.mark.django_db
def test_persist_extracted_facts_clamps_and_dedups():
    organization = OrganizationFactory()
    contact = ContactFactory(organization_id=organization.id)
    conversation = ConversationFactory(contact=contact)
    facts = [
        {"memory_type": "preference", "content": "Prefiere mañana", "importance": 9},
        {"memory_type": "preference", "content": "Prefiere mañana", "importance": 3},  # dup
        {"memory_type": "bogus_type", "content": "ignorar"},  # invalid type
        {"memory_type": "commitment", "content": "  ", "importance": 3},  # empty
        {"memory_type": "objection", "content": "Le parece caro", "importance": -4},
    ]
    created = ConversationMemoryService.persist_extracted_facts(
        conversation=conversation, facts=facts
    )
    assert len(created) == 2
    by_content = {m.content: m for m in created}
    assert by_content["Prefiere mañana"].importance == 5  # clamped to MAX
    assert by_content["Le parece caro"].importance == 1  # clamped to MIN


@pytest.mark.django_db
def test_memory_extract_persist_retrieve_and_inject():
    organization = OrganizationFactory()
    setup_ai_organization(organization)
    contact = ContactFactory(organization_id=organization.id)
    conversation = ConversationFactory(contact=contact)
    MessageFactory(conversation=conversation, body="Pedime la propuesta para el viernes.")

    result = AIGateway.extract_memory(conversation_id=conversation.id)
    assert result.succeeded
    facts = result.data["facts"]
    assert facts  # FakeProvider returns the schema example (3 facts)

    created = ConversationMemoryService.persist_extracted_facts(
        conversation=conversation, facts=facts
    )
    assert len(created) == len(facts)

    retrieved = ConversationMemoryService.memories_for_contact(
        organization_id=organization.id, contact_id=contact.id, limit=6
    )
    assert len(retrieved) == len(facts)
    # Highest importance first.
    assert retrieved[0].importance >= retrieved[-1].importance

    # Selective retrieval is injected into the sales-reply context.
    message = MessageFactory(conversation=conversation, body="hola")
    context = ContextBuilder.for_sales_reply(conversation=conversation, current_message=message)
    assert "contact_memories" in context
    assert "owner_voice" in context
    assert "propuesta" in context["contact_memories"].lower()


@pytest.mark.django_db(transaction=True)
def test_memory_auto_extracts_after_six_inbound_messages():
    organization = OrganizationFactory()
    setup_ai_organization(organization)
    contact = ContactFactory(organization_id=organization.id, type="lead")

    for index in range(6):
        MessageIngestionService.ingest(
            organization=organization,
            channel=Channel.WHATSAPP,
            direction=MessageDirection.INBOUND,
            contact=contact,
            message_type=MessageType.TEXT,
            body=f"Mensaje {index}: recorda que prefiero la mañana.",
        )

    memories = ConversationMemoryService.memories_for_contact(
        organization_id=organization.id,
        contact_id=contact.id,
        limit=10,
    )
    assert len(memories) == 3


@pytest.mark.django_db
def test_memories_are_org_scoped():
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    contact_a = ContactFactory(organization_id=org_a.id)
    conv_a = ConversationFactory(contact=contact_a)
    ConversationMemoryService.create(
        conversation=conv_a, memory_type="preference", content="solo de A", importance=3
    )
    # Same contact id queried under org B must not leak A's memory.
    leaked = ConversationMemoryService.memories_for_contact(
        organization_id=org_b.id, contact_id=contact_a.id, limit=6
    )
    assert leaked == []


@pytest.mark.django_db
def test_sales_reply_renders_with_new_placeholders():
    # Owner voice + contact memories placeholders must not break prompt rendering.
    organization = OrganizationFactory()
    setup_ai_organization(organization)
    contact = ContactFactory(organization_id=organization.id, type="lead")
    conversation = ConversationFactory(contact=contact, mode="sales_ai")
    message = MessageFactory(conversation=conversation, body="hola, ¿me pasás info?")
    result = AIGateway.generate_sales_reply(conversation_id=conversation.id, message_id=message.id)
    assert result.succeeded


@pytest.mark.django_db
def test_generate_project_brief():
    organization = OrganizationFactory()
    setup_ai_organization(organization)
    contact = ContactFactory(organization_id=organization.id)
    conversation = ConversationFactory(contact=contact)
    MessageFactory(conversation=conversation, body="Quieren una app de turnos, backend + web.")

    result = AIGateway.generate_project_brief(
        conversation_id=conversation.id, deal_value_hint="aprox 2M"
    )
    assert result.succeeded
    assert result.purpose == "project_brief"
    assert result.data["title"]
    assert isinstance(result.data["objectives"], list)
