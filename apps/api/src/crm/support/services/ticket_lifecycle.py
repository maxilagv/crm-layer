"""TicketLifecycleService: status transitions, comments and attachments.

Every mutation records a SupportTicketEvent and an audit entry. A critical
ticket can never be resolved by AI alone. Internal comments are never sent to
the client.
"""

from django.db import transaction
from django.utils import timezone

from crm.audit.services import audit_event_create
from crm.core.services.outbox import create_outbox_event
from crm.media.models import MediaAsset
from crm.support.domain import events
from crm.support.domain.enums import (
    ActorType,
    AttachmentType,
    CommentVisibility,
    ResolvedByType,
    TicketEventType,
    TicketStatus,
)
from crm.support.domain.exceptions import CriticalTicketAIResolveDenied
from crm.support.domain.rules import ai_may_resolve, can_reopen
from crm.support.models import (
    SupportResolution,
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketComment,
)

from ._support import org_stub, record_event


def _audit(ticket, *, action, actor, request, **metadata):
    audit_event_create(
        event_type=action,
        actor=actor,
        organization=org_stub(ticket.organization_id),
        request=request,
        resource_type="support_ticket",
        resource_id=str(ticket.id),
        metadata=metadata,
    )


def _emit(ticket, event_type, request, **data):
    create_outbox_event(
        event_type=event_type,
        organization_id=ticket.organization_id,
        payload={
            "event_type": event_type,
            "organization_id": str(ticket.organization_id),
            "data": {"ticket_id": str(ticket.id), **data},
            "metadata": {"request_id": getattr(request, "request_id", None)},
        },
    )


class TicketLifecycleService:
    @staticmethod
    @transaction.atomic
    def assign(*, ticket: SupportTicket, user, actor=None, request=None) -> SupportTicket:
        ticket.assigned_user = user
        if ticket.status not in (
            TicketStatus.RESOLVED.value,
            TicketStatus.CLOSED.value,
            TicketStatus.CANCELLED.value,
        ):
            ticket.status = TicketStatus.IN_PROGRESS
        ticket.save(update_fields=["assigned_user", "status", "updated_at"])
        record_event(
            ticket,
            event_type=TicketEventType.ASSIGNED,
            actor_type=ActorType.USER.value if actor else ActorType.SYSTEM.value,
            actor_id=getattr(actor, "id", None),
            payload={"assigned_user_id": str(user.id)},
        )
        _emit(ticket, events.TICKET_ASSIGNED, request, assigned_user_id=str(user.id))
        _audit(
            ticket,
            action="support_ticket_assigned",
            actor=actor,
            request=request,
            assigned_user_id=str(user.id),
        )
        return ticket

    @staticmethod
    @transaction.atomic
    def change_status(
        *,
        ticket: SupportTicket,
        status: str,
        reason: str = "",
        actor=None,
        actor_type: str = ActorType.USER.value,
        request=None,
    ) -> SupportTicket:
        if ticket.status == status:
            return ticket
        from_status = ticket.status
        ticket.status = status
        ticket.save(update_fields=["status", "updated_at"])
        record_event(
            ticket,
            event_type=TicketEventType.STATUS_CHANGED,
            actor_type=actor_type,
            actor_id=getattr(actor, "id", None),
            from_status=from_status,
            to_status=status,
            payload={"reason": reason[:300]},
        )
        _audit(
            ticket,
            action="support_ticket_updated",
            actor=actor,
            request=request,
            from_status=from_status,
            to_status=status,
        )
        return ticket

    @staticmethod
    @transaction.atomic
    def resolve(
        *,
        ticket: SupportTicket,
        resolution: dict,
        actor=None,
        resolved_by_type: str = ResolvedByType.USER.value,
        ai_run_id=None,
        request=None,
    ) -> SupportTicket:
        # A critical ticket must not be resolved by AI alone.
        if resolved_by_type == ResolvedByType.AI_AGENT.value and not ai_may_resolve(
            ticket.priority
        ):
            raise CriticalTicketAIResolveDenied()

        from_status = ticket.status
        ticket.status = TicketStatus.RESOLVED
        ticket.resolved_at = timezone.now()
        ticket.save(update_fields=["status", "resolved_at", "updated_at"])

        SupportResolution.objects.create(
            organization_id=ticket.organization_id,
            ticket=ticket,
            summary=resolution.get("summary", "")[:5000],
            root_cause=resolution.get("root_cause", ""),
            resolution_steps=resolution.get("resolution_steps", ""),
            resolved_by_id=getattr(actor, "id", None),
            resolved_by_type=resolved_by_type,
            ai_run_id=ai_run_id,
        )
        record_event(
            ticket,
            event_type=TicketEventType.RESOLVED,
            actor_type=ActorType.AI_AGENT.value
            if resolved_by_type == ResolvedByType.AI_AGENT.value
            else ActorType.USER.value,
            actor_id=getattr(actor, "id", None),
            from_status=from_status,
            to_status=TicketStatus.RESOLVED.value,
        )
        _emit(ticket, events.TICKET_RESOLVED, request, resolved_by_type=resolved_by_type)
        _audit(
            ticket,
            action="support_ticket_resolved",
            actor=actor,
            request=request,
            resolved_by_type=resolved_by_type,
        )
        return ticket

    @staticmethod
    @transaction.atomic
    def reopen(
        *, ticket: SupportTicket, reason: str = "", actor=None, request=None
    ) -> SupportTicket:
        if not can_reopen(ticket.status):
            return ticket
        from_status = ticket.status
        ticket.status = TicketStatus.IN_PROGRESS if ticket.assigned_user_id else TicketStatus.OPEN
        ticket.resolved_at = None
        ticket.save(update_fields=["status", "resolved_at", "updated_at"])
        record_event(
            ticket,
            event_type=TicketEventType.REOPENED,
            actor_type=ActorType.USER.value if actor else ActorType.SYSTEM.value,
            actor_id=getattr(actor, "id", None),
            from_status=from_status,
            to_status=ticket.status,
            payload={"reason": reason[:300]},
        )
        _emit(ticket, events.TICKET_REOPENED, request, reason=reason[:200])
        _audit(ticket, action="support_ticket_reopened", actor=actor, request=request)
        return ticket

    @staticmethod
    @transaction.atomic
    def close(*, ticket: SupportTicket, actor=None, request=None) -> SupportTicket:
        return TicketLifecycleService.change_status(
            ticket=ticket,
            status=TicketStatus.CLOSED.value,
            reason="closed",
            actor=actor,
            request=request,
        )

    @staticmethod
    @transaction.atomic
    def add_comment(
        *,
        ticket: SupportTicket,
        body: str,
        visibility: str = CommentVisibility.INTERNAL.value,
        actor=None,
        author_type: str = ActorType.USER.value,
        request=None,
    ) -> SupportTicketComment:
        comment = SupportTicketComment.objects.create(
            organization_id=ticket.organization_id,
            ticket=ticket,
            author_type=author_type,
            author_id=getattr(actor, "id", None),
            body=body,
            visibility=visibility,
        )
        record_event(
            ticket,
            event_type=TicketEventType.COMMENT_ADDED,
            actor_type=author_type,
            actor_id=getattr(actor, "id", None),
            payload={"comment_id": str(comment.id), "visibility": visibility},
        )
        _emit(
            ticket,
            events.TICKET_COMMENT_ADDED,
            request,
            comment_id=str(comment.id),
            visibility=visibility,
        )
        _audit(
            ticket,
            action="support_ticket_comment_added",
            actor=actor,
            request=request,
            visibility=visibility,
        )
        return comment

    @staticmethod
    @transaction.atomic
    def add_attachment(
        *,
        ticket: SupportTicket,
        media_asset_id,
        attachment_type: str = AttachmentType.OTHER.value,
        source_message_id=None,
        actor=None,
        request=None,
    ) -> SupportTicketAttachment:
        media_asset = MediaAsset.objects.get(
            id=media_asset_id, organization_id=ticket.organization_id
        )
        attachment = SupportTicketAttachment.objects.create(
            organization_id=ticket.organization_id,
            ticket=ticket,
            media_asset=media_asset,
            source_message_id=source_message_id,
            attachment_type=attachment_type,
        )
        record_event(
            ticket,
            event_type=TicketEventType.ATTACHMENT_ADDED,
            actor_type=ActorType.USER.value if actor else ActorType.SYSTEM.value,
            actor_id=getattr(actor, "id", None),
            payload={"attachment_id": str(attachment.id), "type": attachment_type},
        )
        _emit(ticket, events.TICKET_ATTACHMENT_ADDED, request, attachment_id=str(attachment.id))
        _audit(
            ticket,
            action="support_ticket_attachment_added",
            actor=actor,
            request=request,
            attachment_type=attachment_type,
        )
        return attachment
