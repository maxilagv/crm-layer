import ast
import uuid
from pathlib import Path

import pytest
from django.utils import timezone

from crm.ai.providers.fake_provider import FakeAIProvider
from crm.automations.domain.enums import AutomationActionType, AutomationTriggerType
from crm.automations.domain.policies import ACTION_PERMISSIONS
from crm.automations.services.automation_rule_service import AutomationRuleService
from crm.automations.services.trigger_dispatcher import TriggerDispatcher
from crm.contacts.constants import ContactType
from crm.core.models import OutboxEvent
from crm.core.security.permissions import Role
from crm.notifications.domain.enums import (
    NotificationDeliveryStatus,
    NotificationPriority,
    NotificationType,
)
from crm.notifications.models import Notification, NotificationDelivery, NotificationPreference
from crm.notifications.services.notification_service import NotificationService
from crm.support.domain.enums import TicketPriority
from crm.support.models import SupportTicket
from crm.tasks.domain.enums import TaskReminderStatus, TaskStatus
from crm.tasks.models import Task, TaskCommand, TaskReminder, TaskSource, TaskStatusHistory
from crm.tasks.services.task_command_parser import TaskCommandParser
from crm.tasks.services.task_creator import TaskCreator
from crm.tasks.services.task_escalation import TaskEscalationService
from crm.tasks.services.task_extractor import TaskExtractor
from crm.tasks.services.task_reminder import TaskReminderService
from tests.factories.accounts import UserFactory
from tests.factories.ai import setup_ai_organization
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory, MessageFactory
from tests.factories.leads import LeadFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory


@pytest.fixture(autouse=True)
def _reset_fake_provider():
    FakeAIProvider.reset()
    yield
    FakeAIProvider.reset()


def _member(role: Role = Role.OPERATOR):
    user = UserFactory(phone="+5491111111111")
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=role.value)
    return user, organization


def _auth(api_client, user, organization):
    api_client.force_authenticate(user=user)
    return {"HTTP_X_ORGANIZATION_ID": str(organization.id)}


def _conversation(organization, body="Manana le paso presupuesto a Juan."):
    contact = ContactFactory(organization_id=organization.id, type=ContactType.LEAD)
    conversation = ConversationFactory(organization_id=organization.id, contact=contact)
    message = MessageFactory(conversation=conversation, contact=contact, body=body)
    return contact, conversation, message


@pytest.mark.django_db
def test_task_created_manually_with_history_source_and_reminder():
    user, organization = _member()
    contact, _conversation_obj, _message = _conversation(organization)
    due_at = timezone.now() + timezone.timedelta(hours=2)

    task, created = TaskCreator.create_manual(
        organization=organization,
        title="Llamar a Juan",
        priority="high",
        due_at=due_at,
        contact_id=contact.id,
        assigned_to=user,
        actor=user,
        idempotency_key="manual-juan",
    )
    same_task, same_created = TaskCreator.create_manual(
        organization=organization,
        title="Llamar a Juan",
        priority="high",
        due_at=due_at,
        contact_id=contact.id,
        assigned_to=user,
        actor=user,
        idempotency_key="manual-juan",
    )

    assert created is True
    assert same_created is False
    assert same_task.id == task.id
    assert TaskStatusHistory.objects.filter(task=task, to_status=TaskStatus.PENDING).count() == 1
    assert TaskSource.objects.filter(task=task, source_type="manual").exists()
    assert TaskReminder.objects.filter(task=task, status=TaskReminderStatus.PENDING).count() == 1


@pytest.mark.django_db
def test_task_extracted_from_message_and_duplicate_prevented():
    _user, organization = _member()
    setup_ai_organization(organization)
    _contact, conversation, message = _conversation(organization)
    fake_output = {
        "tasks": [
            {
                "title": "Enviar presupuesto a Juan",
                "description": "Compromiso detectado en conversacion.",
                "due_at": (timezone.now() + timezone.timedelta(days=1)).isoformat(),
                "priority": "high",
                "confidence": 0.91,
                "requires_confirmation": False,
            }
        ]
    }

    first = TaskExtractor.extract_from_message(
        organization=organization,
        conversation=conversation,
        message=message,
        metadata={"fake_output": fake_output},
    )
    second = TaskExtractor.extract_from_message(
        organization=organization,
        conversation=conversation,
        message=message,
        metadata={"fake_output": fake_output},
    )

    assert first.created_count == 1
    assert second.created_count == 0
    assert (
        Task.objects.filter(organization_id=organization.id, source_type="ai_extracted").count()
        == 1
    )


@pytest.mark.django_db
def test_invalid_ai_output_does_not_create_task():
    _user, organization = _member()
    setup_ai_organization(organization)
    _contact, conversation, message = _conversation(organization)

    result = TaskExtractor.extract_from_message(
        organization=organization,
        conversation=conversation,
        message=message,
        metadata={"fake_behavior": "invalid_schema"},
    )

    assert result.created_count == 0
    assert Task.objects.filter(organization_id=organization.id).count() == 0


@pytest.mark.django_db
def test_due_reminder_sends_notification_and_completed_task_does_not_notify():
    user, organization = _member()
    due_at = timezone.now() - timezone.timedelta(minutes=5)
    active, _ = TaskCreator.create_manual(
        organization=organization,
        title="Responder lead",
        priority="high",
        due_at=due_at,
        assigned_to=user,
    )
    completed, _ = TaskCreator.create_manual(
        organization=organization,
        title="No recordar",
        priority="high",
        due_at=due_at,
        assigned_to=user,
    )
    completed.status = TaskStatus.COMPLETED.value
    completed.completed_at = timezone.now()
    completed.save(update_fields=["status", "completed_at", "updated_at"])

    sent = TaskReminderService.send_due(organization=organization)

    assert sent == 1
    assert Notification.objects.filter(resource_type="task", resource_id=active.id).count() == 1
    assert Notification.objects.filter(resource_type="task", resource_id=completed.id).count() == 0


@pytest.mark.django_db
def test_owner_command_hecho_completes_task_and_client_command_rejected():
    user, organization = _member()
    task, _ = TaskCreator.create_manual(
        organization=organization,
        title="Cerrar pendiente",
        assigned_to=user,
    )
    owner_contact = ContactFactory(
        organization_id=organization.id,
        type=ContactType.INTERNAL,
        metadata={"is_owner": True},
    )
    conversation = ConversationFactory(organization_id=organization.id, contact=owner_contact)
    owner_message = MessageFactory(
        organization_id=organization.id,
        conversation=conversation,
        contact=owner_contact,
        body="HECHO",
        metadata={"task_id": str(task.id)},
    )

    command = TaskCommandParser.parse_and_apply(
        organization=organization,
        message=owner_message,
        task=task,
        actor=user,
    )
    command_again = TaskCommandParser.parse_and_apply(
        organization=organization,
        message=owner_message,
        task=task,
        actor=user,
    )
    task.refresh_from_db()

    assert task.status == TaskStatus.COMPLETED.value
    assert command.status == "processed"
    assert command_again.id == command.id

    client_contact = ContactFactory(organization_id=organization.id, type=ContactType.CLIENT)
    client_conversation = ConversationFactory(
        organization_id=organization.id, contact=client_contact
    )
    client_message = MessageFactory(
        organization_id=organization.id,
        conversation=client_conversation,
        contact=client_contact,
        body="HECHO",
    )
    rejected = TaskCommandParser.parse_and_apply(
        organization=organization,
        message=client_message,
        task=task,
        actor=user,
    )
    assert rejected.status == "rejected"
    assert TaskCommand.objects.filter(message=client_message, status="rejected").exists()


@pytest.mark.django_db
def test_owner_command_posponer_snoozes_task():
    user, organization = _member()
    task, _ = TaskCreator.create_manual(
        organization=organization, title="Seguimiento", assigned_to=user
    )
    owner_contact = ContactFactory(organization_id=organization.id, metadata={"is_owner": True})
    conversation = ConversationFactory(organization_id=organization.id, contact=owner_contact)
    message = MessageFactory(
        organization_id=organization.id,
        conversation=conversation,
        contact=owner_contact,
        body="POSPONER 2H",
        metadata={"task_id": str(task.id)},
    )

    TaskCommandParser.parse_and_apply(
        organization=organization, message=message, task=task, actor=user
    )
    task.refresh_from_db()

    assert task.status == TaskStatus.SNOOZED.value
    assert task.due_at is not None
    assert task.metadata["snooze_count"] == 1


@pytest.mark.django_db
def test_overdue_task_escalates_once():
    user, organization = _member()
    task, _ = TaskCreator.create_manual(
        organization=organization,
        title="Tarea vencida",
        priority="urgent",
        due_at=timezone.now() - timezone.timedelta(days=1),
        assigned_to=user,
    )

    first = TaskEscalationService.escalate_overdue(organization=organization)
    second = TaskEscalationService.escalate_overdue(organization=organization)
    task.refresh_from_db()

    assert first == 1
    assert second == 0
    assert task.status == TaskStatus.OVERDUE.value
    assert Notification.objects.filter(type=NotificationType.TASK_OVERDUE.value).count() == 1


@pytest.mark.django_db
def test_notification_rate_limit_suppresses_whatsapp_spam():
    user, organization = _member()
    NotificationPreference.objects.create(
        organization_id=organization.id,
        recipient_user=user,
        channel="whatsapp",
        max_per_hour=1,
    )

    NotificationService.notify_owner(
        organization=organization,
        notification_type=NotificationType.SYSTEM_ALERT.value,
        title="Alerta 1",
        priority=NotificationPriority.HIGH.value,
        resource_type="test",
        resource_id=uuid.uuid4(),
    )
    NotificationService.notify_owner(
        organization=organization,
        notification_type=NotificationType.AI_FAILURE.value,
        title="Alerta 2",
        priority=NotificationPriority.HIGH.value,
        resource_type="test",
        resource_id=uuid.uuid4(),
    )

    assert (
        NotificationDelivery.objects.filter(
            channel="whatsapp", status=NotificationDeliveryStatus.QUEUED
        ).count()
        == 1
    )
    assert OutboxEvent.objects.filter(event_type="notification.suppressed.v1").count() == 1


@pytest.mark.django_db
def test_hot_lead_automation_creates_task_and_notification():
    user, organization = _member(Role.OWNER)
    lead = LeadFactory(organization_id=organization.id, score=85)
    rule = AutomationRuleService.create(
        organization=organization,
        actor=user,
        name="Hot lead",
        trigger_type=AutomationTriggerType.LEAD_BECAME_HOT.value,
        conditions=[{"field": "score", "operator": "gte", "value": 80}],
        actions=[
            {
                "type": AutomationActionType.CREATE_TASK.value,
                "configuration": {"title": "Llamar lead caliente", "priority": "urgent"},
            },
            {
                "type": AutomationActionType.NOTIFY_OWNER.value,
                "configuration": {
                    "notification_type": NotificationType.HOT_LEAD.value,
                    "title": "Lead caliente",
                    "body": "Score {score}",
                    "priority": NotificationPriority.URGENT.value,
                    "resource_type": "lead",
                    "resource_id_field": "lead_id",
                },
            },
        ],
    )

    runs = TriggerDispatcher.dispatch(
        organization=organization,
        trigger_type=AutomationTriggerType.LEAD_BECAME_HOT.value,
        payload={"lead_id": str(lead.id), "score": 85, "id": str(lead.id)},
        trigger_event_id="lead-hot-1",
    )

    assert len(runs) == 1
    runs[0].refresh_from_db()
    assert runs[0].status == "success"
    assert Task.objects.filter(title="Llamar lead caliente").count() == 1
    assert Notification.objects.filter(type=NotificationType.HOT_LEAD.value).count() == 1
    assert runs[0].steps.count() == 3
    assert rule.action_rows.count() == 2


@pytest.mark.django_db
def test_urgent_ticket_automation_notifies_and_disabled_rule_is_logged_skipped():
    user, organization = _member(Role.OWNER)
    contact = ContactFactory(organization_id=organization.id)
    ticket = SupportTicket.objects.create(
        organization_id=organization.id,
        contact=contact,
        title="Sistema caido",
        priority=TicketPriority.URGENT.value,
    )
    AutomationRuleService.create(
        organization=organization,
        actor=user,
        name="Ticket urgente",
        trigger_type=AutomationTriggerType.TICKET_CREATED.value,
        conditions=[{"field": "priority", "operator": "eq", "value": "urgent"}],
        actions=[
            {
                "type": AutomationActionType.NOTIFY_OWNER.value,
                "configuration": {
                    "notification_type": NotificationType.URGENT_TICKET.value,
                    "title": "Ticket urgente",
                    "body": "{title}",
                    "priority": NotificationPriority.URGENT.value,
                    "resource_type": "support_ticket",
                    "resource_id_field": "ticket_id",
                },
            }
        ],
    )
    AutomationRuleService.create(
        organization=organization,
        actor=user,
        name="Disabled",
        trigger_type=AutomationTriggerType.TICKET_CREATED.value,
        is_enabled=False,
        actions=[
            {"type": AutomationActionType.CREATE_TASK.value, "configuration": {"title": "No"}}
        ],
    )

    runs = TriggerDispatcher.dispatch(
        organization=organization,
        trigger_type=AutomationTriggerType.TICKET_CREATED.value,
        payload={"ticket_id": str(ticket.id), "priority": "urgent", "title": ticket.title},
        trigger_event_id="ticket-urgent-1",
    )

    statuses = sorted(run.status for run in runs)
    assert statuses == ["skipped", "success"]
    assert Notification.objects.filter(type=NotificationType.URGENT_TICKET.value).count() == 1


@pytest.mark.django_db
def test_action_invalid_permission_blocked():
    viewer = UserFactory()
    organization = OrganizationFactory(owner=viewer)
    MembershipFactory(organization=organization, user=viewer, role=Role.VIEWER.value)
    lead = LeadFactory(organization_id=organization.id)
    rule = AutomationRuleService.create(
        organization=organization,
        actor=viewer,
        name="Bad update",
        trigger_type=AutomationTriggerType.LEAD_SCORE_CHANGED.value,
        actions=[
            {
                "type": AutomationActionType.UPDATE_LEAD_STAGE.value,
                "configuration": {"stage": "hot"},
                "required_permission": ACTION_PERMISSIONS[
                    AutomationActionType.UPDATE_LEAD_STAGE.value
                ],
            }
        ],
    )

    run = TriggerDispatcher.dispatch(
        organization=organization,
        trigger_type=AutomationTriggerType.LEAD_SCORE_CHANGED.value,
        payload={"lead_id": str(lead.id), "score": 90},
        trigger_event_id="lead-score-1",
    )[0]

    run.refresh_from_db()
    assert run.status == "failed"
    assert run.steps.first().error_code == "permission_denied"
    assert rule.action_rows.first().required_permission == "leads.update"


@pytest.mark.django_db
def test_phase8_api_crud(api_client):
    user, organization = _member(Role.OPERATOR)
    headers = _auth(api_client, user, organization)
    created = api_client.post(
        "/api/v1/tasks/",
        {"title": "Tarea API", "priority": "medium"},
        format="json",
        **headers,
    )
    assert created.status_code == 201
    task_id = created.json()["data"]["id"]
    completed = api_client.post(f"/api/v1/tasks/{task_id}/complete/", {}, format="json", **headers)
    assert completed.status_code == 200
    assert completed.json()["data"]["status"] == "completed"

    pref = api_client.patch(
        "/api/v1/notification-preferences/",
        {"max_per_hour": 2},
        format="json",
        **headers,
    )
    assert pref.status_code == 200
    assert pref.json()["data"]["max_per_hour"] == 2

    rule = api_client.post(
        "/api/v1/automations/rules/",
        {
            "name": "API rule",
            "trigger_type": "task_due",
            "actions": [{"type": "create_task", "configuration": {"title": "Desde automation"}}],
        },
        format="json",
        **headers,
    )
    assert rule.status_code == 201
    listed = api_client.get("/api/v1/automations/rules/", **headers)
    assert listed.status_code == 200
    assert listed.json()["pagination"]["total"] == 1


def test_tasks_notifications_automations_do_not_import_openai_anthropic_or_meta_clients():
    root = Path(__file__).resolve().parents[2] / "src" / "crm"
    forbidden_roots = {"openai", "anthropic"}
    forbidden_names = {"MetaClient", "TemplateClient", "MediaClient"}
    offenders = []
    for module in ["tasks", "notifications", "automations"]:
        for path in (root / module).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in forbidden_roots:
                            offenders.append(str(path))
                if isinstance(node, ast.ImportFrom):
                    if (node.module or "").split(".")[0] in forbidden_roots:
                        offenders.append(str(path))
                    for alias in node.names:
                        if alias.name in forbidden_names:
                            offenders.append(str(path))
    assert offenders == []
