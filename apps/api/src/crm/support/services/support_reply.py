"""SupportReplyService: generate a safe suggested reply for a client message.

Delegates to ``AIGateway.generate_support_reply`` which already runs SafetyGuard
(blocks password/token requests, escalates legal threats, etc.) for the
support_reply purpose. This service adds ticket linkage and owner notification,
and never sends WhatsApp directly — the caller decides whether/how to send.
"""

from dataclasses import dataclass, field

from crm.support.models import SupportTicket
from crm.support.services.urgent_ticket_notifier import SupportUrgentTicketNotifier


@dataclass(frozen=True)
class SupportReplyResult:
    run_id: str | None
    reply: str
    can_send: bool
    decision: str
    requires_handoff: bool
    missing_information: list[str] = field(default_factory=list)
    owner_notified: bool = False


class SupportReplyService:
    @staticmethod
    def generate(
        *, conversation_id, message_id, ticket_id=None, actor=None, request=None
    ) -> SupportReplyResult:
        from crm.ai.services.ai_gateway import AIGateway

        result = AIGateway.generate_support_reply(
            conversation_id=conversation_id,
            message_id=message_id,
            ticket_id=ticket_id,
            actor=actor,
        )
        data = result.data or {}
        safety = result.safety
        decision = safety.decision if safety else "send"
        requires_handoff = bool(safety and safety.requires_handoff)
        owner_notified = False

        # Notify the owner if the model or SafetyGuard asked for it and we have a ticket.
        should_notify = bool(data.get("should_notify_owner")) or (
            safety and safety.owner_notification_required
        )
        if should_notify and ticket_id:
            ticket = SupportTicket.objects.filter(id=ticket_id).first()
            if ticket is not None:
                owner_notified = SupportUrgentTicketNotifier.notify(
                    ticket=ticket, reason="support_reply_flagged", actor=actor, request=request
                )

        return SupportReplyResult(
            run_id=str(result.run_id) if result.run_id else None,
            reply=data.get("reply", result.text),
            can_send=result.can_send_reply,
            decision=decision,
            requires_handoff=requires_handoff,
            missing_information=data.get("missing_information", []),
            owner_notified=owner_notified,
        )
