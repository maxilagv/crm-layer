"""Conversation engine for Cazador replies and follow-ups."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.core.cache import cache
from django.db.models import F, Q
from django.utils import timezone

from crm.ai.domain.enums import SafetyDecision
from crm.ai.services.ai_gateway import AIGateway
from crm.ai.services.safety_guard import SafetyGuard
from crm.notifications.domain.enums import NotificationPriority, NotificationType
from crm.notifications.services.notification_service import NotificationService
from crm.prospecting.domain.enums import CampaignStatus, ProspectStatus
from crm.prospecting.models import Prospect
from crm.whatsapp.models import OutboundMessage

from .outreach import ProspectOutreachService, _next_followup_slot, _org_stub

logger = logging.getLogger(__name__)

_REPLY_SEND_ACTIONS = {"ask_qualifying", "propose_call", "send_info", "rebut_objection"}
_DRAFT_ACTIONS = _REPLY_SEND_ACTIONS | {"handoff_human"}
_FOLLOWUP_LOCK_TTL = 60 * 60
_REPLY_MODE = "reply"
_FOLLOWUP_MODE = "followup"
_FOLLOWUP_LIMIT = 100


@dataclass(frozen=True)
class ConversationActionResult:
    queued: bool = False
    notified: bool = False
    reason: str = ""


def handle_inbound_next_step(
    *,
    organization,
    prospect: Prospect,
    conversation,
    contact,
    message,
    intent: str,
    next_action: str,
    objection_type: str = "",
    actor=None,
    request=None,
) -> ConversationActionResult:
    if prospect.status in (
        ProspectStatus.DO_NOT_CONTACT.value,
        ProspectStatus.NOT_INTERESTED.value,
    ):
        return ConversationActionResult(reason="terminal_status")

    if intent == "maybe" or next_action == "schedule_followup":
        _schedule_followup(prospect=prospect)
        if next_action == "schedule_followup":
            return ConversationActionResult(reason="followup_scheduled")

    if next_action not in _DRAFT_ACTIONS:
        return ConversationActionResult(reason="no_action")

    ai = AIGateway.draft_prospect_reply(
        prospect_id=prospect.id,
        conversation_id=conversation.id,
        message_id=message.id,
        mode=_REPLY_MODE,
        intent=intent,
        next_action=next_action,
        objection_type=objection_type,
        last_outbound=_latest_outbound_body(prospect),
        actor=actor,
        metadata={"source": "prospecting_inbound_reply"},
        http_request=request,
    )
    if not ai.succeeded or not ai.data:
        _notify_owner(
            organization=organization,
            prospect=prospect,
            title=f"Revisar respuesta de {prospect.business_name}",
            body="Cazador no pudo generar una respuesta segura para este prospecto.",
            metadata={
                "mode": _REPLY_MODE,
                "intent": intent,
                "next_action": next_action,
                "message_id": str(message.id),
                "reason": ai.error_code or ai.error_message or "draft_failed",
            },
            deduplication_key=f"prospecting-reply-draft-failed:{message.id}",
        )
        return ConversationActionResult(notified=True, reason="draft_failed")

    return _route_draft(
        organization=organization,
        prospect=prospect,
        conversation=conversation,
        contact=contact,
        inbound_text=message.body or "",
        message=str(ai.data.get("message") or "").strip(),
        should_send=bool(ai.data.get("should_send", False)),
        handoff=bool(ai.data.get("handoff", False)) or next_action == "handoff_human",
        reason=str(ai.data.get("reason") or ""),
        mode=_REPLY_MODE,
        intent=intent,
        next_action=next_action,
        objection_type=objection_type,
        idempotency_key=f"prospecting:{prospect.id}:reply:{message.id}",
        notification_key=f"prospecting-reply-draft:{message.id}",
        actor=actor,
        request=request,
    )


def run_due_followups(*, now=None, limit: int = _FOLLOWUP_LIMIT) -> int:
    now = now or timezone.now()
    queued_count = 0
    for prospect in _due_followup_prospects(now=now, limit=limit):
        if not cache.add(f"prospecting:followup:{prospect.id}", 1, timeout=_FOLLOWUP_LOCK_TTL):
            continue
        result = _run_followup_for_prospect(prospect=prospect, now=now)
        if result.queued:
            queued_count += 1
    return queued_count


def _run_followup_for_prospect(*, prospect: Prospect, now) -> ConversationActionResult:
    prospect = Prospect.objects.select_related("campaign").get(
        id=prospect.id,
        organization_id=prospect.organization_id,
    )
    if not _still_due_for_followup(prospect=prospect, now=now):
        return ConversationActionResult(reason="not_due")

    organization = _org_stub(prospect.organization_id)
    conversation = None
    if prospect.conversation_id:
        from crm.conversations.models import Conversation

        conversation = Conversation.objects.filter(
            organization_id=prospect.organization_id,
            id=prospect.conversation_id,
        ).first()

    ai = AIGateway.draft_prospect_reply(
        prospect_id=prospect.id,
        conversation_id=prospect.conversation_id,
        mode=_FOLLOWUP_MODE,
        intent="maybe",
        next_action="schedule_followup",
        objection_type="",
        last_outbound=_latest_outbound_body(prospect),
        metadata={"source": "prospecting_followup"},
    )
    if not ai.succeeded or not ai.data:
        _notify_owner(
            organization=organization,
            prospect=prospect,
            title=f"Follow-up pendiente: {prospect.business_name}",
            body="Cazador no pudo generar un follow-up seguro.",
            metadata={
                "mode": _FOLLOWUP_MODE,
                "reason": ai.error_code or ai.error_message or "draft_failed",
            },
            deduplication_key=f"prospecting-followup-draft-failed:{prospect.id}:{now.date()}",
        )
        return ConversationActionResult(notified=True, reason="draft_failed")

    contact = None
    if prospect.contact_id:
        from crm.contacts.models import Contact

        contact = Contact.objects.filter(
            organization_id=prospect.organization_id,
            id=prospect.contact_id,
        ).first()

    return _route_draft(
        organization=organization,
        prospect=prospect,
        conversation=conversation,
        contact=contact,
        inbound_text="",
        message=str(ai.data.get("message") or "").strip(),
        should_send=bool(ai.data.get("should_send", False)),
        handoff=bool(ai.data.get("handoff", False)),
        reason=str(ai.data.get("reason") or ""),
        mode=_FOLLOWUP_MODE,
        intent="maybe",
        next_action="schedule_followup",
        objection_type="",
        idempotency_key=f"prospecting:{prospect.id}:followup:{prospect.follow_up_count + 1}",
        notification_key=f"prospecting-followup-draft:{prospect.id}:{prospect.follow_up_count + 1}",
        count_followup=True,
    )


def _route_draft(
    *,
    organization,
    prospect: Prospect,
    conversation,
    contact,
    inbound_text: str,
    message: str,
    should_send: bool,
    handoff: bool,
    reason: str,
    mode: str,
    intent: str,
    next_action: str,
    objection_type: str,
    idempotency_key: str,
    notification_key: str,
    actor=None,
    request=None,
    count_followup: bool = False,
) -> ConversationActionResult:
    if not message:
        return ConversationActionResult(reason="empty_draft")

    safety = SafetyGuard.evaluate_reply(
        organization_id=prospect.organization_id,
        proposed_reply=message,
        inbound_text=inbound_text,
        purpose="outreach_reply",
        model_requests_handoff=handoff,
    )
    should_notify = (
        handoff
        or not should_send
        or (mode == _REPLY_MODE and not prospect.campaign.auto_reply)
        or (mode == _FOLLOWUP_MODE and not prospect.campaign.auto_followup)
        or safety.decision != SafetyDecision.SEND.value
    )
    if should_notify:
        _notify_owner(
            organization=organization,
            prospect=prospect,
            title=_notification_title(prospect=prospect, mode=mode, handoff=handoff),
            body=message,
            metadata={
                "suggested_reply": message,
                "mode": mode,
                "intent": intent,
                "next_action": next_action,
                "objection_type": objection_type,
                "reason": reason,
                "safety": safety.as_dict(),
            },
            deduplication_key=notification_key,
            actor=actor,
            request=request,
        )
        return ConversationActionResult(notified=True, reason="owner_notified")

    attempt = ProspectOutreachService.queue_generated_message(
        prospect=prospect,
        body=message,
        kind=mode,
        idempotency_key=idempotency_key,
        conversation=conversation,
        contact=contact,
        actor=actor,
        request=request,
        count_followup=count_followup,
        schedule_followup=prospect.campaign.auto_followup,
    )
    if attempt.queued:
        return ConversationActionResult(queued=True, reason="")

    _notify_owner(
        organization=organization,
        prospect=prospect,
        title=f"Respuesta pendiente: {prospect.business_name}",
        body=message,
        metadata={
            "suggested_reply": message,
            "mode": mode,
            "intent": intent,
            "next_action": next_action,
            "objection_type": objection_type,
            "reason": attempt.reason,
        },
        deduplication_key=f"{notification_key}:blocked:{attempt.reason}",
        actor=actor,
        request=request,
    )
    return ConversationActionResult(notified=True, reason=attempt.reason)


def _due_followup_prospects(*, now, limit: int):
    limit = max(1, min(int(limit or _FOLLOWUP_LIMIT), _FOLLOWUP_LIMIT))
    stale_cutoff = now - timedelta(days=3)
    return list(
        Prospect.objects.select_related("campaign")
        .filter(
            campaign__status=CampaignStatus.ACTIVE.value,
            campaign__auto_followup=True,
            status__in=(ProspectStatus.CONTACTED.value, ProspectStatus.REPLIED.value),
            phone__gt="",
            touch_count__lt=F("campaign__max_touches"),
        )
        .filter(
            Q(next_followup_at__lte=now)
            | Q(next_followup_at__isnull=True, last_touch_at__lte=stale_cutoff)
            | Q(
                next_followup_at__isnull=True,
                last_touch_at__isnull=True,
                contacted_at__lte=stale_cutoff,
            )
        )
        .exclude(
            status__in=(ProspectStatus.DO_NOT_CONTACT.value, ProspectStatus.NOT_INTERESTED.value)
        )
        .order_by("next_followup_at", "last_touch_at", "contacted_at")[:limit]
    )


def _still_due_for_followup(*, prospect: Prospect, now) -> bool:
    campaign = prospect.campaign
    if campaign.status != CampaignStatus.ACTIVE.value or not campaign.auto_followup:
        return False
    if prospect.status not in (ProspectStatus.CONTACTED.value, ProspectStatus.REPLIED.value):
        return False
    if int(prospect.touch_count or 0) >= int(campaign.max_touches or 0):
        return False
    if prospect.next_followup_at is not None:
        return prospect.next_followup_at <= now
    anchor = prospect.last_touch_at or prospect.contacted_at
    return bool(anchor and anchor <= now - timedelta(days=3))


def _schedule_followup(*, prospect: Prospect) -> None:
    Prospect.objects.filter(id=prospect.id, organization_id=prospect.organization_id).update(
        next_followup_at=_next_followup_slot(
            now=timezone.now(),
            follow_up_count=prospect.follow_up_count,
        ),
        updated_at=timezone.now(),
    )


def _notify_owner(
    *,
    organization,
    prospect: Prospect,
    title: str,
    body: str,
    metadata: dict,
    deduplication_key: str,
    actor=None,
    request=None,
) -> None:
    NotificationService.notify_owner(
        organization=organization,
        notification_type=NotificationType.CALL_REQUESTED.value,
        title=title,
        body=body,
        priority=NotificationPriority.HIGH.value,
        resource_type="prospecting_prospect",
        resource_id=prospect.id,
        metadata={"campaign_id": str(prospect.campaign_id), **metadata},
        deduplication_key=deduplication_key,
        actor=actor,
        request=request,
    )


def _notification_title(*, prospect: Prospect, mode: str, handoff: bool) -> str:
    if handoff:
        return f"Revisar conversacion: {prospect.business_name}"
    if mode == _FOLLOWUP_MODE:
        return f"Follow-up sugerido: {prospect.business_name}"
    return f"Respuesta sugerida: {prospect.business_name}"


def _latest_outbound_body(prospect: Prospect) -> str:
    outbound = (
        OutboundMessage.objects.filter(
            organization_id=prospect.organization_id,
            prospect_id=prospect.id,
        )
        .order_by("-created_at")
        .first()
    )
    return outbound.body if outbound else ""
