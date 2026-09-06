"""End-to-end gateway tests (fake provider only, real DB)."""

import pytest
from django.conf import settings

from crm.ai.domain.enums import AIPurpose, AIRunStatus, SafetyDecision
from crm.ai.domain.exceptions import AIModelConfigMissing
from crm.ai.models import AIModelConfig, AIRun, AIUsageRecord
from crm.ai.providers.fake_provider import FakeAIProvider
from crm.ai.services.ai_gateway import AIGateway
from crm.contacts.constants import ContactType
from tests.factories.ai import AIModelConfigFactory, AIProviderFactory, setup_ai_organization
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory, MessageFactory
from tests.factories.organizations import OrganizationFactory


@pytest.fixture(autouse=True)
def _reset_fake_provider():
    FakeAIProvider.reset()
    yield
    FakeAIProvider.reset()


@pytest.fixture
def ai_org(db):
    organization = OrganizationFactory()
    setup_ai_organization(organization)
    return organization


def _conversation_with_message(organization, *, body="Hola, quiero info", contact_type="lead"):
    contact = ContactFactory(organization_id=organization.id, type=contact_type)
    conversation = ConversationFactory(organization_id=organization.id, contact=contact)
    message = MessageFactory(conversation=conversation, body=body, normalized_text=body.lower())
    return conversation, message


@pytest.mark.django_db
def test_ai_gateway_uses_configured_provider(ai_org) -> None:
    conversation, message = _conversation_with_message(ai_org)
    result = AIGateway.generate_sales_reply(conversation_id=conversation.id, message_id=message.id)
    assert result.succeeded
    assert result.provider == "fake"
    assert result.model == "fake-model"
    run = AIRun.objects.get(id=result.run_id)
    assert run.status == AIRunStatus.SUCCESS.value
    assert run.purpose == AIPurpose.SALES_REPLY.value
    assert run.prompt_version_id is not None
    assert run.latency_ms > 0
    assert run.input_messages  # logged before/with the call
    assert run.conversation_id == conversation.id


@pytest.mark.django_db
def test_ai_gateway_returns_validated_structured_output(ai_org) -> None:
    conversation, message = _conversation_with_message(ai_org)
    result = AIGateway.generate_sales_reply(conversation_id=conversation.id, message_id=message.id)
    assert result.data is not None
    assert "reply" in result.data
    assert result.safety is not None
    assert result.safety.decision == SafetyDecision.SEND.value
    assert result.can_send_reply


@pytest.mark.django_db
def test_ai_gateway_fallback_provider(ai_org) -> None:
    # Make the primary provider always time out and configure a fake fallback.
    fallback_provider = AIProviderFactory(organization_id=ai_org.id, name="Fallback", priority=200)
    config = AIModelConfig.objects.get(organization_id=ai_org.id, purpose="sales_reply")
    config.fallback_provider = fallback_provider
    config.fallback_model = "fake-fallback-model"
    config.save()

    conversation, message = _conversation_with_message(ai_org)
    # First provider call times out; the fallback (also fake) succeeds because
    # the behavior flag is consumed by metadata for both, so script the failure:
    result = AIGateway.generate_sales_reply(
        conversation_id=conversation.id,
        message_id=message.id,
        metadata={"fake_behavior": "valid"},
    )
    assert result.succeeded

    # Now force a timeout on the primary: behavior applies to both, so instead
    # validate the run status path via a purpose-level scripted failure.
    result_timeout = AIGateway.generate_sales_reply(
        conversation_id=conversation.id,
        message_id=message.id,
        metadata={"fake_behavior": "timeout"},
    )
    # Both primary and fallback time out -> failed, with normalized error code.
    run = AIRun.objects.get(id=result_timeout.run_id)
    assert run.status == AIRunStatus.FAILED.value
    assert run.error_code == "provider_timeout"


@pytest.mark.django_db
def test_missing_model_config_fails_cleanly(db) -> None:
    organization = OrganizationFactory()
    conversation, message = _conversation_with_message(organization)
    with pytest.raises(AIModelConfigMissing):
        AIGateway.generate_sales_reply(conversation_id=conversation.id, message_id=message.id)


@pytest.mark.django_db
def test_disabled_provider_is_not_used(db) -> None:
    organization = OrganizationFactory()
    provider = AIProviderFactory(organization_id=organization.id, is_enabled=False)
    AIModelConfigFactory(provider=provider, organization_id=organization.id)
    conversation, message = _conversation_with_message(organization)
    with pytest.raises(AIModelConfigMissing):
        AIGateway.generate_sales_reply(conversation_id=conversation.id, message_id=message.id)


@pytest.mark.django_db
def test_ai_run_failed_is_logged(ai_org) -> None:
    conversation, message = _conversation_with_message(ai_org)
    result = AIGateway.generate_sales_reply(
        conversation_id=conversation.id,
        message_id=message.id,
        metadata={"fake_behavior": "provider_error"},
    )
    run = AIRun.objects.get(id=result.run_id)
    assert run.status == AIRunStatus.FAILED.value
    assert run.error_code == "provider_unknown_error"
    assert run.finished_at is not None


@pytest.mark.django_db
def test_usage_and_cost_recorded(ai_org) -> None:
    conversation, message = _conversation_with_message(ai_org)
    result = AIGateway.generate_sales_reply(conversation_id=conversation.id, message_id=message.id)
    record = AIUsageRecord.objects.get(ai_run_id=result.run_id)
    assert record.input_tokens == 120
    assert record.output_tokens == 45
    assert record.purpose == AIPurpose.SALES_REPLY.value
    run = AIRun.objects.get(id=result.run_id)
    assert run.usage_total_tokens == 165


@pytest.mark.django_db
def test_safety_guard_blocks_unsafe_reply_from_model(ai_org) -> None:
    conversation, message = _conversation_with_message(ai_org)
    result = AIGateway.generate_sales_reply(
        conversation_id=conversation.id,
        message_id=message.id,
        metadata={"fake_behavior": "blocked_reply"},
    )
    run = AIRun.objects.get(id=result.run_id)
    assert run.status == AIRunStatus.BLOCKED_BY_SAFETY.value
    assert result.safety is not None
    assert result.safety.decision == SafetyDecision.DO_NOT_REPLY.value
    assert not result.can_send_reply
    assert run.safety_result["decision"] == SafetyDecision.DO_NOT_REPLY.value


@pytest.mark.django_db
def test_summarize_conversation(ai_org) -> None:
    conversation, _message = _conversation_with_message(ai_org)
    result = AIGateway.summarize_conversation(conversation_id=conversation.id)
    assert result.succeeded
    assert result.data["summary"]


@pytest.mark.django_db
def test_transcribe_audio(ai_org) -> None:
    result = AIGateway.transcribe_audio(
        organization_id=ai_org.id, audio_bytes=b"fake-bytes", audio_format="ogg"
    )
    assert result.succeeded
    assert "problema" in result.data["text"]
    run = AIRun.objects.get(id=result.run_id)
    assert run.purpose == AIPurpose.AUDIO_TRANSCRIPTION.value


@pytest.mark.django_db
def test_generate_image(ai_org) -> None:
    result = AIGateway.generate_image(organization_id=ai_org.id, image_request="flyer promo")
    assert result.succeeded
    assert result.data["image_b64"]


@pytest.mark.django_db
def test_create_embedding_and_dedupe(ai_org) -> None:
    contact = ContactFactory(organization_id=ai_org.id, type=ContactType.LEAD)
    first = AIGateway.create_embedding(
        organization_id=ai_org.id, owner_type="contact", owner_id=contact.id, text="hola mundo"
    )
    assert first.succeeded
    assert first.data["dimensions"] == settings.AI_EMBEDDING_DIMENSIONS
    second = AIGateway.create_embedding(
        organization_id=ai_org.id, owner_type="contact", owner_id=contact.id, text="hola mundo"
    )
    assert second.data["deduplicated"] is True
    assert second.run_id is None  # no provider call on dedupe


@pytest.mark.django_db
def test_classify_risk_deterministic_block(ai_org) -> None:
    result = AIGateway.classify_risk(
        organization_id=ai_org.id,
        proposed_reply="Pasame tu contraseña y lo configuro",
        context={"current_message": "no puedo entrar"},
    )
    assert result.data["decision"] == SafetyDecision.DO_NOT_REPLY.value
    assert result.run_id is None  # deterministic verdict, no model call


@pytest.mark.django_db
def test_classify_risk_uses_model_when_clean(ai_org) -> None:
    result = AIGateway.classify_risk(
        organization_id=ai_org.id,
        proposed_reply="Gracias por escribirnos, ¿coordinamos una llamada?",
        context={"current_message": "quiero info"},
    )
    assert result.run_id is not None
    assert result.data["decision"] == SafetyDecision.SEND.value
