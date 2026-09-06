import uuid

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings

from crm.ai.domain.enums import AIPurpose
from crm.ai.models import AIEmbedding
from crm.ai.providers.fake_provider import FakeAIProvider
from crm.ai.services.ai_gateway import AIGateway
from crm.ai.services.context_builder import ContextBuilder
from crm.knowledge.models import KnowledgeChunk, KnowledgeSource
from crm.knowledge.selectors.knowledge_search import KnowledgeRetriever
from crm.knowledge.services.knowledge_ingestion import KnowledgeIngestionService
from tests.factories.ai import setup_ai_organization
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory, MessageFactory
from tests.factories.organizations import OrganizationFactory


@pytest.fixture(autouse=True)
def _reset_fake_and_cache():
    FakeAIProvider.reset()
    cache.clear()


def _setup_embeddings(organization):
    setup_ai_organization(
        organization,
        purposes=[AIPurpose.EMBEDDING.value],
        seed_prompts=False,
    )


def _source(organization, *, name: str = "Knowledge") -> KnowledgeSource:
    return KnowledgeSource.objects.create(
        organization_id=organization.id,
        name=name,
        source_type=KnowledgeSource.SourceType.MANUAL_TEXT,
        status=KnowledgeSource.Status.ACTIVE,
    )


def _conversation(organization, *, body: str):
    contact = ContactFactory(organization_id=organization.id)
    conversation = ConversationFactory(contact=contact)
    message = MessageFactory(conversation=conversation, body=body)
    return conversation, message


@pytest.mark.django_db
def test_embedding_vectorfield_width_and_dimension_mismatch() -> None:
    organization = OrganizationFactory()
    _setup_embeddings(organization)
    owner_id = uuid.uuid4()

    result = AIGateway.create_embedding(
        organization_id=organization.id,
        owner_type="test_owner",
        owner_id=owner_id,
        text="vector 768 ok",
    )

    assert result.succeeded
    embedding = AIEmbedding.objects.get(owner_id=owner_id)
    assert len(embedding.vector) == settings.AI_EMBEDDING_DIMENSIONS

    bad_owner_id = uuid.uuid4()
    failed = AIGateway.create_embedding(
        organization_id=organization.id,
        owner_type="test_owner",
        owner_id=bad_owner_id,
        text="bad vector",
        metadata={"fake_embedding_vector": [0.1, 0.2, 0.3, 0.4]},
    )

    assert failed.error_code == "embedding_dim_mismatch"
    assert not AIEmbedding.objects.filter(owner_id=bad_owner_id).exists()


@pytest.mark.django_db
@override_settings(KNOWLEDGE_CHUNK_SIZE=20, KNOWLEDGE_CHUNK_OVERLAP=5)
def test_knowledge_chunking_uses_overlap() -> None:
    organization = OrganizationFactory()
    _setup_embeddings(organization)
    source = _source(organization)

    document = KnowledgeIngestionService.ingest_text(
        organization_id=organization.id,
        source=source,
        title="Overlapping",
        raw_text="abcdefghijklmnopqrstuvwxyz0123456789",
    )

    chunks = list(KnowledgeChunk.objects.filter(document=document).order_by("chunk_index"))
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].content[-5:] == chunks[1].content[:5]


@pytest.mark.django_db
def test_knowledge_ingestion_dedupes_same_content() -> None:
    organization = OrganizationFactory()
    _setup_embeddings(organization)
    source = _source(organization)

    first = KnowledgeIngestionService.ingest_text(
        organization_id=organization.id,
        source=source,
        title="Pricing",
        raw_text="Plan Pro includes onboarding and priority support.",
    )
    embedding_count = AIEmbedding.objects.count()
    second = KnowledgeIngestionService.ingest_text(
        organization_id=organization.id,
        source=source,
        title="Pricing copy",
        raw_text="Plan Pro includes onboarding and priority support.",
    )

    assert second.id == first.id
    assert AIEmbedding.objects.count() == embedding_count


@pytest.mark.django_db
def test_knowledge_search_top_k_is_tenant_scoped_and_does_not_persist_query_vector() -> None:
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    _setup_embeddings(org_a)
    _setup_embeddings(org_b)
    source_a = _source(org_a, name="A")
    source_b = _source(org_b, name="B")
    exact = "The enterprise plan includes SSO and quarterly business reviews."

    KnowledgeIngestionService.ingest_text(
        organization_id=org_a.id,
        source=source_a,
        title="Enterprise",
        raw_text=exact,
    )
    KnowledgeIngestionService.ingest_text(
        organization_id=org_a.id,
        source=source_a,
        title="Starter",
        raw_text="The starter plan includes email support only.",
    )
    KnowledgeIngestionService.ingest_text(
        organization_id=org_b.id,
        source=source_b,
        title="Other tenant",
        raw_text=exact,
    )
    before = AIEmbedding.objects.count()

    results = KnowledgeRetriever.search(organization_id=org_a.id, query_text=exact, k=2)

    assert len(results) == 2
    assert results[0].chunk.organization_id == org_a.id
    assert results[0].chunk.content == exact
    assert all(result.chunk.organization_id == org_a.id for result in results)
    assert AIEmbedding.objects.count() == before


@pytest.mark.django_db
@override_settings(KNOWLEDGE_CONTEXT_TOKEN_BUDGET=10, KNOWLEDGE_CHUNK_SIZE=80)
def test_context_builder_injects_knowledge_with_budget_and_skips_provider_when_empty(
    monkeypatch,
) -> None:
    organization = OrganizationFactory()
    _setup_embeddings(organization)
    source = _source(organization)
    query = "Cancellation requires 30 days notice before renewal."
    KnowledgeIngestionService.ingest_text(
        organization_id=organization.id,
        source=source,
        title="Policy",
        raw_text=query,
    )
    conversation, message = _conversation(organization, body=query)

    context = ContextBuilder.for_sales_reply(conversation=conversation, current_message=message)

    assert context["knowledge_chunks"] != "Sin conocimiento relevante."
    injected = context["knowledge_chunks"].split(": ", 1)[1]
    assert len(injected) <= settings.KNOWLEDGE_CONTEXT_TOKEN_BUDGET * 4

    empty_org = OrganizationFactory()
    empty_conversation, empty_message = _conversation(empty_org, body="Any knowledge?")

    def fail_if_called(**_kwargs):
        raise AssertionError("query embedding provider should not be called for empty KB")

    monkeypatch.setattr(AIGateway, "create_embedding_vector", fail_if_called)
    empty = ContextBuilder.for_sales_reply(
        conversation=empty_conversation,
        current_message=empty_message,
    )
    assert empty["knowledge_chunks"] == "Sin conocimiento relevante."


@pytest.mark.django_db
def test_knowledge_retrieval_failures_are_best_effort(monkeypatch) -> None:
    organization = OrganizationFactory()
    _setup_embeddings(organization)
    source = _source(organization)
    KnowledgeIngestionService.ingest_text(
        organization_id=organization.id,
        source=source,
        title="Support",
        raw_text="Refunds are reviewed manually by the owner.",
    )

    results = KnowledgeRetriever.search(
        organization_id=organization.id,
        query_text="Refunds are reviewed manually by the owner.",
        metadata={"fake_behavior": "provider_error"},
    )
    assert results == []

    def fail_search(**_kwargs):
        raise RuntimeError("simulated retrieve failure")

    monkeypatch.setattr(KnowledgeRetriever, "search", fail_search)
    block = ContextBuilder._knowledge_chunks("refunds", organization.id)
    assert block == "Sin conocimiento relevante."
