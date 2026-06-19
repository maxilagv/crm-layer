"""Structured output validation + retry policy tests."""

import pytest

from crm.ai.domain.enums import AIPurpose, AIRunStatus
from crm.ai.models import AIRun
from crm.ai.providers.fake_provider import FakeAIProvider
from crm.ai.schemas import LeadScoreSchema
from crm.ai.services.ai_gateway import AIGateway
from crm.ai.services.structured_output import StructuredOutputValidator
from tests.factories.ai import setup_ai_organization
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory, MessageFactory
from tests.factories.organizations import OrganizationFactory


@pytest.fixture(autouse=True)
def _reset_fake_provider():
    FakeAIProvider.reset()
    yield
    FakeAIProvider.reset()


def test_structured_output_validation_accepts_valid_payload() -> None:
    result = StructuredOutputValidator.validate(
        AIPurpose.LEAD_SCORING.value, LeadScoreSchema.example
    )
    assert result.is_valid
    assert result.data["score"] == 82


def test_invalid_schema_rejected_with_errors() -> None:
    result = StructuredOutputValidator.validate(
        AIPurpose.LEAD_SCORING.value, {"score": 999, "temperature": "volcanic"}
    )
    assert not result.is_valid
    assert any("score" in error for error in result.errors)


def test_enum_hallucination_is_rejected() -> None:
    payload = {**LeadScoreSchema.example, "temperature": "volcanic"}
    result = StructuredOutputValidator.validate(AIPurpose.LEAD_SCORING.value, payload)
    assert not result.is_valid


def test_unknown_extra_fields_are_rejected() -> None:
    payload = {**LeadScoreSchema.example, "campo_alucinado": True}
    result = StructuredOutputValidator.validate(AIPurpose.LEAD_SCORING.value, payload)
    assert not result.is_valid


@pytest.mark.django_db
def test_invalid_schema_retries_once_then_succeeds() -> None:
    organization = OrganizationFactory()
    setup_ai_organization(organization)
    contact = ContactFactory(organization_id=organization.id, type="lead")
    conversation = ConversationFactory(organization_id=organization.id, contact=contact)
    message = MessageFactory(conversation=conversation, body="hola")

    result = AIGateway.generate_sales_reply(
        conversation_id=conversation.id,
        message_id=message.id,
        metadata={"fake_behavior": "invalid_then_valid"},
    )
    assert result.succeeded
    assert result.data is not None


@pytest.mark.django_db
def test_invalid_schema_twice_marks_run_schema_invalid_and_no_db_writes() -> None:
    organization = OrganizationFactory()
    setup_ai_organization(organization)
    contact = ContactFactory(organization_id=organization.id, type="lead")
    conversation = ConversationFactory(organization_id=organization.id, contact=contact)
    message = MessageFactory(conversation=conversation, body="hola")

    result = AIGateway.generate_sales_reply(
        conversation_id=conversation.id,
        message_id=message.id,
        metadata={"fake_behavior": "invalid_schema"},
    )
    run = AIRun.objects.get(id=result.run_id)
    assert run.status == AIRunStatus.SCHEMA_INVALID.value
    assert result.data is None
    assert run.output_json is None  # invalid output never persisted as validated
    # No tool calls, no safety pass, nothing else mutated.
    assert run.tool_call_records.count() == 0
