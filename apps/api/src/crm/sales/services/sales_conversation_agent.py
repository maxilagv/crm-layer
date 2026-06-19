from datetime import timedelta

from django.utils import timezone

from crm.ai.services.ai_gateway import AIGateway
from crm.audit.services import audit_event_create
from crm.conversations.models import Conversation, Message
from crm.core.services.outbox import create_outbox_event
from crm.leads.domain import events as lead_events
from crm.leads.services.lead_creation import create_or_get_lead_from_conversation
from crm.leads.services.lead_qualification import detect_unqualified_from_text
from crm.leads.services.lead_scoring import score_lead
from crm.sales.domain import events
from crm.sales.domain.rules import classify_intent
from crm.sales.domain.value_objects import SalesAgentResult

from .followup_service import create_followup
from .opportunity_service import create_or_update_opportunity_for_lead
from .sales_call_closer import create_call_request
from .sales_objection_handler import detect_and_record_objection
from .sales_reply_policy import SalesReplyPolicy


class SalesConversationAgent:
    @staticmethod
    def generate_reply(
        *,
        conversation: Conversation,
        message: Message,
        organization,
        actor=None,
        request=None,
        ai_metadata: dict | None = None,
    ) -> SalesAgentResult:
        creation = create_or_get_lead_from_conversation(
            organization=organization,
            conversation=conversation,
            message=message,
            explicit=False,
            actor=actor,
            request=request,
        )
        if creation.lead is None:
            return SalesAgentResult(
                reply="",
                intent=classify_intent(message.body),
                lead=None,
                ai_run_id=None,
                blocked=True,
                reasons=[creation.reason],
            )
        lead = creation.lead
        score_lead(lead=lead, conversation=conversation, actor=actor, metadata=ai_metadata or {})
        lead.refresh_from_db()

        objection = detect_and_record_objection(
            lead=lead, message=message, conversation=conversation, text=message.body
        )
        unqualified = detect_unqualified_from_text(lead=lead, text=message.body, actor=actor)
        if unqualified is not None:
            lead = unqualified

        result = AIGateway.generate_sales_reply(
            conversation_id=conversation.id,
            message_id=message.id,
            lead_id=lead.id,
            actor=actor,
            metadata=ai_metadata or {},
            http_request=request,
        )
        if not result.data:
            _emit_blocked(
                lead=lead,
                ai_run_id=result.run_id,
                reasons=[result.error_code or "ai_reply_failed"],
            )
            return SalesAgentResult(
                reply="",
                intent=classify_intent(message.body),
                lead=lead,
                ai_run_id=result.run_id,
                blocked=True,
                reasons=[result.error_code or "ai_reply_failed"],
            )

        data = result.data
        reply = str(data.get("reply") or "")
        policy = SalesReplyPolicy.evaluate(
            organization_id=organization.id,
            reply=reply,
            inbound_text=message.body,
        )
        if not result.can_send_reply or not policy.allowed:
            reasons = [*(policy.reasons or [])]
            if result.safety and not result.safety.allows_send:
                reasons.extend(result.safety.reasons)
            _emit_blocked(lead=lead, ai_run_id=result.run_id, reasons=reasons)
            return SalesAgentResult(
                reply=reply,
                intent=str(data.get("intent") or classify_intent(message.body)),
                lead=lead,
                ai_run_id=result.run_id,
                blocked=True,
                reasons=reasons,
            )

        _apply_lead_updates(lead=lead, updates=data.get("lead_updates") or {})

        should_call = bool(data.get("should_create_call_request")) or str(data.get("intent")) in {
            "propose_call",
            "book_call",
        }
        if should_call:
            create_call_request(
                lead=lead,
                conversation=conversation,
                notes="Solicitud creada por agente vendedor.",
                actor=actor,
            )

        for task in data.get("suggested_tasks") or []:
            title = str(task.get("title") or "Seguimiento comercial")
            create_followup(
                lead=lead,
                conversation=conversation,
                due_at=timezone.now() + timedelta(days=2),
                title=title,
                notes=str(task.get("description") or ""),
                actor=actor,
            )

        create_or_update_opportunity_for_lead(lead=lead, actor=actor)
        if bool(data.get("should_notify_owner")) or lead.score >= 76:
            notify_owner_for_hot_lead(lead=lead, reason="hot_lead_or_ai_requested")

        create_outbox_event(
            event_type=events.SALES_REPLY_READY,
            organization_id=organization.id,
            payload={
                "lead_id": str(lead.id),
                "conversation_id": str(conversation.id),
                "message_id": str(message.id),
                "ai_run_id": str(result.run_id),
                "reply": reply,
                "intent": str(data.get("intent") or classify_intent(message.body)),
            },
        )
        audit_event_create(
            event_type="sales_reply_generated",
            actor=actor,
            organization=organization,
            request=request,
            resource_type="lead",
            resource_id=str(lead.id),
            metadata={
                "ai_run_id": str(result.run_id),
                "objection_id": str(getattr(objection, "id", "") or ""),
            },
        )
        return SalesAgentResult(
            reply=reply,
            intent=str(data.get("intent") or classify_intent(message.body)),
            lead=lead,
            ai_run_id=result.run_id,
            sent_to_gateway=True,
        )


def notify_owner_for_hot_lead(*, lead, reason: str = "hot_lead") -> bool:
    metadata = dict(lead.metadata or {})
    if metadata.get("hot_owner_notified_at"):
        return False
    metadata["hot_owner_notified_at"] = timezone.now().isoformat()
    metadata["hot_owner_notification_reason"] = reason
    lead.metadata = metadata
    lead.save(update_fields=["metadata", "updated_at"])
    create_outbox_event(
        event_type=events.SALES_HOT_LEAD_OWNER_NOTIFICATION,
        organization_id=lead.organization_id,
        payload={"lead_id": str(lead.id), "score": lead.score, "reason": reason},
    )
    create_outbox_event(
        event_type=lead_events.LEAD_HOT_DETECTED,
        organization_id=lead.organization_id,
        payload={"lead_id": str(lead.id), "score": lead.score},
    )
    audit_event_create(
        event_type="sales_hot_lead_owner_notified",
        organization=_org_stub(lead.organization_id),
        resource_type="lead",
        resource_id=str(lead.id),
        metadata={"score": lead.score, "reason": reason},
    )
    return True


def _emit_blocked(*, lead, ai_run_id, reasons: list[str]) -> None:
    create_outbox_event(
        event_type=events.SALES_REPLY_BLOCKED,
        organization_id=lead.organization_id,
        payload={"lead_id": str(lead.id), "ai_run_id": str(ai_run_id or ""), "reasons": reasons},
    )


def _apply_lead_updates(*, lead, updates: dict) -> None:
    allowed_fields = {
        "service_interest",
        "budget_signal",
        "urgency",
        "authority_signal",
        "pain_points",
        "technical_needs",
        "business_needs",
        "next_best_action",
        "summary",
    }
    changed = []
    for field, value in (updates or {}).items():
        if field not in allowed_fields:
            continue
        setattr(lead, field, value)
        changed.append(field)
    if changed:
        lead.save(update_fields=[*changed, "updated_at"])


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()
