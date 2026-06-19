"""ToolExecutor pipeline tests: permissions, validation, idempotency, errors."""

import pytest

from crm.ai.domain.enums import AIPurpose, ToolCallStatus
from crm.ai.domain.value_objects import AIToolRequest
from crm.ai.models import AIRun, AIToolCall
from crm.ai.tools import ToolContext, ToolExecutor, register_builtin_tools
from crm.conversations.constants import ConversationMode
from crm.core.models import OutboxEvent
from tests.factories.conversations import ConversationFactory
from tests.factories.organizations import OrganizationFactory

register_builtin_tools()


def _context(organization, **kwargs) -> ToolContext:
    run = AIRun.objects.create(organization_id=organization.id, purpose=AIPurpose.SALES_REPLY.value)
    return ToolContext(
        organization_id=organization.id,
        ai_run=run,
        purpose=kwargs.pop("purpose", AIPurpose.SALES_REPLY.value),
        **kwargs,
    )


@pytest.mark.django_db
def test_unregistered_tool_is_blocked() -> None:
    organization = OrganizationFactory()
    result = ToolExecutor.execute(
        request=AIToolRequest(tool_name="drop_database", arguments={}),
        context=_context(organization),
    )
    assert result.status == ToolCallStatus.BLOCKED.value
    record = AIToolCall.objects.get(id=result.tool_call_record_id)
    assert record.status == ToolCallStatus.BLOCKED.value


@pytest.mark.django_db
def test_tool_call_validates_arguments() -> None:
    organization = OrganizationFactory()
    result = ToolExecutor.execute(
        request=AIToolRequest(tool_name="create_task", arguments={"title": 123}),
        context=_context(organization),
    )
    assert result.status == ToolCallStatus.FAILED.value
    assert result.error_code == "tool_validation_error"


@pytest.mark.django_db
def test_tool_call_wrong_purpose_is_blocked() -> None:
    organization = OrganizationFactory()
    result = ToolExecutor.execute(
        request=AIToolRequest(tool_name="create_task", arguments={"title": "X"}),
        context=_context(organization, purpose=AIPurpose.IMAGE_GENERATION.value),
    )
    assert result.status == ToolCallStatus.BLOCKED.value
    assert result.error_code == "tool_permission_denied"


@pytest.mark.django_db
def test_tool_call_executes_and_creates_outbox_event() -> None:
    organization = OrganizationFactory()
    result = ToolExecutor.execute(
        request=AIToolRequest(tool_name="create_task", arguments={"title": "Llamar a Juan"}),
        context=_context(organization),
    )
    assert result.status == ToolCallStatus.EXECUTED.value
    assert result.result["deferred_via_outbox"] is True
    assert OutboxEvent.objects.filter(
        event_type="ai.task_candidate_created.v1", organization_id=organization.id
    ).exists()


@pytest.mark.django_db
def test_tool_call_idempotency_prevents_duplicate_task() -> None:
    organization = OrganizationFactory()
    context = _context(organization)
    request = AIToolRequest(tool_name="create_task", arguments={"title": "Llamar a Juan"})

    first = ToolExecutor.execute(request=request, context=context)
    second = ToolExecutor.execute(request=request, context=context)

    assert first.status == ToolCallStatus.EXECUTED.value
    assert second.status == ToolCallStatus.DUPLICATE.value
    # Only ONE side effect happened.
    assert (
        OutboxEvent.objects.filter(
            event_type="ai.task_candidate_created.v1", organization_id=organization.id
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_tool_unavailable_module_fails_controlled() -> None:
    # create_ticket IS allowed for the AI agent role (tickets.manage), but its
    # backing module does not exist yet: controlled failure, never fake success.
    organization = OrganizationFactory()
    result = ToolExecutor.execute(
        request=AIToolRequest(
            tool_name="create_ticket",
            arguments={"title": "Bug en turnos", "description": "No carga"},
        ),
        context=_context(organization, purpose=AIPurpose.SUPPORT_REPLY.value),
    )
    assert result.status == ToolCallStatus.FAILED.value
    assert result.error_code == "tool_module_unavailable"


@pytest.mark.django_db
def test_update_lead_blocked_for_ai_agent_without_actor() -> None:
    # The AI agent role lacks leads.update: autonomous lead mutation is denied.
    organization = OrganizationFactory()
    result = ToolExecutor.execute(
        request=AIToolRequest(
            tool_name="update_lead",
            arguments={"lead_id": "x", "updates": {"stage": "qualified"}},
        ),
        context=_context(organization),
    )
    assert result.status == ToolCallStatus.BLOCKED.value
    assert result.error_code == "tool_permission_denied"


@pytest.mark.django_db
def test_tool_result_is_attached_to_ai_run() -> None:
    organization = OrganizationFactory()
    context = _context(organization)
    ToolExecutor.execute(
        request=AIToolRequest(tool_name="notify_owner", arguments={"reason": "lead caliente"}),
        context=context,
    )
    assert context.ai_run.tool_call_records.count() == 1
    record = context.ai_run.tool_call_records.first()
    assert record.tool_name == "notify_owner"
    assert record.status == ToolCallStatus.EXECUTED.value


@pytest.mark.django_db
def test_pause_conversation_tool_pauses_real_conversation() -> None:
    organization = OrganizationFactory()
    conversation = ConversationFactory(
        organization_id=organization.id, mode=ConversationMode.SALES_AI, ai_enabled=True
    )
    result = ToolExecutor.execute(
        request=AIToolRequest(tool_name="pause_conversation_ai", arguments={}),
        context=_context(organization, conversation_id=conversation.id),
    )
    assert result.status == ToolCallStatus.EXECUTED.value
    conversation.refresh_from_db()
    assert conversation.mode == ConversationMode.PAUSED.value
    assert conversation.ai_enabled is False


@pytest.mark.django_db
def test_send_whatsapp_blocked_by_safety() -> None:
    organization = OrganizationFactory()
    conversation = ConversationFactory(organization_id=organization.id)
    result = ToolExecutor.execute(
        request=AIToolRequest(
            tool_name="send_whatsapp_message",
            arguments={"body": "Pasame tu contraseña para configurarlo"},
        ),
        context=_context(organization, conversation_id=conversation.id),
    )
    assert result.status == ToolCallStatus.FAILED.value
    assert result.error_code == "safety_blocked"
