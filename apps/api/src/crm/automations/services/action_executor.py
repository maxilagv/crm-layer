from crm.automations.domain.enums import AutomationActionType
from crm.automations.domain.exceptions import AutomationPermissionDenied
from crm.automations.domain.policies import ACTION_PERMISSIONS
from crm.automations.domain.value_objects import ActionResult
from crm.conversations.models import Conversation
from crm.conversations.services import ConversationHandoffService
from crm.core.security.permissions import can
from crm.core.services.outbox import create_outbox_event
from crm.leads.domain.enums import LeadStage
from crm.leads.models import Lead
from crm.leads.services.lead_lifecycle import change_stage
from crm.notifications.domain.enums import NotificationPriority, NotificationType
from crm.notifications.services.notification_service import NotificationService
from crm.sales.services.followup_service import create_followup
from crm.support.domain.enums import ActorType, TicketEventType, TicketPriority
from crm.support.models import SupportTicket
from crm.support.services._support import record_event
from crm.tasks.services.task_creator import TaskCreator


class ActionExecutor:
    @staticmethod
    def execute(*, organization, action, payload: dict) -> ActionResult:
        try:
            _assert_permission(organization=organization, action=action)
            action_type = action.action_type
            config = dict(action.configuration or {})
            if action_type == AutomationActionType.NOTIFY_OWNER.value:
                notification, created = NotificationService.notify_owner(
                    organization=organization,
                    notification_type=config.get(
                        "notification_type", NotificationType.SYSTEM_ALERT.value
                    ),
                    title=_render(config.get("title", "Notificacion operativa"), payload),
                    body=_render(config.get("body", ""), payload),
                    priority=config.get("priority", NotificationPriority.HIGH.value),
                    resource_type=config.get("resource_type", ""),
                    resource_id=payload.get(config.get("resource_id_field", "id")),
                    deduplication_key=config.get("deduplication_key", ""),
                )
                return ActionResult(
                    True, {"notification_id": str(notification.id), "created": created}
                )
            if action_type == AutomationActionType.CREATE_TASK.value:
                task, created = TaskCreator.create(
                    organization=organization,
                    title=_render(config.get("title", "Tarea automatica"), payload),
                    description=_render(config.get("description", ""), payload),
                    priority=config.get("priority", "medium"),
                    source_type="automation",
                    source_id=payload.get("id"),
                    idempotency_key=config.get("idempotency_key")
                    or f"automation-task:{action.id}:{payload.get('id', '')}",
                    metadata={"automation_action_id": str(action.id), "trigger_payload": payload},
                )
                return ActionResult(True, {"task_id": str(task.id), "created": created})
            if action_type == AutomationActionType.UPDATE_LEAD_STAGE.value:
                lead = Lead.objects.filter(
                    organization_id=organization.id,
                    id=payload.get("lead_id") or config.get("lead_id"),
                ).first()
                if lead is None:
                    return ActionResult(False, {}, "lead_not_found", "Lead not found")
                stage = config.get("stage", LeadStage.QUALIFYING.value)
                change_stage(lead=lead, to_stage=stage, reason="automation")
                return ActionResult(True, {"lead_id": str(lead.id), "stage": stage})
            if action_type == AutomationActionType.CREATE_TICKET.value:
                ticket = _create_ticket_adapter(
                    organization=organization, config=config, payload=payload
                )
                return ActionResult(True, {"ticket_id": str(ticket.id)})
            if action_type == AutomationActionType.PAUSE_AI.value:
                conversation = Conversation.objects.filter(
                    organization_id=organization.id,
                    id=payload.get("conversation_id") or config.get("conversation_id"),
                ).first()
                if conversation is None:
                    return ActionResult(
                        False, {}, "conversation_not_found", "Conversation not found"
                    )
                ConversationHandoffService.pause_ai(
                    conversation=conversation, actor=organization.owner
                )
                return ActionResult(True, {"conversation_id": str(conversation.id)})
            if action_type == AutomationActionType.SCHEDULE_FOLLOWUP.value:
                lead = Lead.objects.filter(
                    organization_id=organization.id,
                    id=payload.get("lead_id") or config.get("lead_id"),
                ).first()
                if lead is None:
                    return ActionResult(False, {}, "lead_not_found", "Lead not found")
                followup, created = create_followup(
                    lead=lead,
                    due_at=config["due_at"],
                    title=config.get("title", "Follow-up comercial"),
                    idempotency_key=f"automation-followup:{action.id}:{lead.id}",
                )
                return ActionResult(True, {"followup_id": str(followup.id), "created": created})
            if action_type == AutomationActionType.SEND_WHATSAPP_MESSAGE.value:
                if not config.get("policy_approved"):
                    return ActionResult(
                        False, {}, "policy_required", "WhatsApp action requires policy_approved"
                    )
                create_outbox_event(
                    event_type="automation.whatsapp_message_requested.v1",
                    organization_id=organization.id,
                    payload={
                        "action_id": str(action.id),
                        "payload": payload,
                        "configuration": config,
                    },
                )
                return ActionResult(True, {"queued": True})
            return ActionResult(False, {}, "unsupported_action", action_type)
        except AutomationPermissionDenied as exc:
            return ActionResult(False, {}, "permission_denied", str(exc))
        except Exception as exc:
            return ActionResult(False, {}, "action_failed", str(exc))


def _assert_permission(*, organization, action) -> None:
    permission = action.required_permission or ACTION_PERMISSIONS.get(action.action_type, "")
    if not permission:
        return
    actor = action.rule.created_by
    if actor is None and action.configuration.get("system_allowed"):
        return
    if not can(actor, permission, organization):
        raise AutomationPermissionDenied(f"Action requires {permission}")


def _render(template: str, payload: dict) -> str:
    text = str(template or "")
    for key, value in payload.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def _create_ticket_adapter(*, organization, config: dict, payload: dict) -> SupportTicket:
    from crm.contacts.models import Contact

    contact = Contact.objects.filter(
        organization_id=organization.id,
        id=payload.get("contact_id") or config.get("contact_id"),
    ).first()
    if contact is None:
        raise ValueError("create_ticket requires contact_id")
    ticket = SupportTicket.objects.create(
        organization_id=organization.id,
        contact=contact,
        title=_render(config.get("title", "Ticket automatico"), payload),
        description=_render(config.get("description", ""), payload),
        priority=config.get("priority", TicketPriority.MEDIUM.value),
        source_message_id=payload.get("message_id") or config.get("source_message_id"),
        conversation_id=payload.get("conversation_id") or config.get("conversation_id"),
    )
    record_event(
        ticket,
        event_type=TicketEventType.CREATED.value,
        actor_type=ActorType.SYSTEM.value,
        payload={"source": "automation"},
    )
    return ticket
