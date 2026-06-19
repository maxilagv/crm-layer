"""Outbound orchestration for Cazador prospects."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import time, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from crm.ai.services.ai_gateway import AIGateway
from crm.audit.services import audit_event_create
from crm.contacts.constants import ContactStatus
from crm.contacts.services import ContactResolver
from crm.core.services.outbox import create_outbox_event
from crm.prospecting.domain import events
from crm.prospecting.domain.enums import CONTACTED_STATUSES, CampaignStatus, ProspectStatus
from crm.prospecting.models import Prospect, ProspectingCampaign
from crm.whatsapp.models import OutboundMessage
from crm.whatsapp.services.outbound_queue import WhatsAppOutboundQueueService

BUSINESS_START = time(9, 0)
BUSINESS_END = time(18, 0)
DEFAULT_JITTER_MAX_SECONDS = 15 * 60
FOLLOW_UP_DELAYS_DAYS = (3, 7, 14)


@dataclass(frozen=True)
class OutreachAttempt:
    prospect: Prospect
    queued: bool
    reason: str = ""


class ProspectOutreachService:
    @staticmethod
    def run_campaign(
        *,
        campaign: ProspectingCampaign,
        limit: int = 50,
        actor=None,
        request=None,
    ) -> list[OutreachAttempt]:
        attempts: list[OutreachAttempt] = []
        for index, prospect in enumerate(_eligible_prospects(campaign)[:limit]):
            attempts.append(
                ProspectOutreachService.contact_prospect(
                    prospect=prospect,
                    actor=actor,
                    request=request,
                    jitter_seconds=index * 60 + random.randint(0, 45),
                )
            )
        return attempts

    @staticmethod
    def contact_prospect(
        *,
        prospect: Prospect,
        actor=None,
        request=None,
        now=None,
        jitter_seconds: int | None = None,
    ) -> OutreachAttempt:
        prospect = Prospect.objects.select_related("campaign").get(
            id=prospect.id,
            organization_id=prospect.organization_id,
        )
        allowed, reason = _can_contact(prospect)
        if not allowed:
            if reason == "missing_phone":
                _mark_failed(prospect=prospect, reason=reason, actor=actor, request=request)
                prospect.refresh_from_db()
            return OutreachAttempt(prospect=prospect, queued=False, reason=reason)

        daily_used = _daily_outbound_count(prospect.campaign)
        if daily_used >= prospect.campaign.daily_cap:
            return OutreachAttempt(prospect=prospect, queued=False, reason="daily_cap_reached")

        ai = AIGateway.draft_outreach_opener(
            prospect_id=prospect.id,
            actor=actor,
            metadata={"source": "prospecting_outreach"},
            http_request=request,
        )
        if not ai.succeeded or not ai.data or not (ai.data.get("message") or "").strip():
            _mark_failed(
                prospect=prospect,
                reason=ai.error_code or ai.error_message or "outreach_opener_failed",
                actor=actor,
                request=request,
            )
            prospect.refresh_from_db()
            return OutreachAttempt(prospect=prospect, queued=False, reason="opener_failed")

        body = str(ai.data["message"]).strip()
        available_at = _next_business_slot(now=now, jitter_seconds=jitter_seconds)
        queued = WhatsAppOutboundQueueService.enqueue(
            organization=_org_stub(prospect.organization_id),
            phone=prospect.phone,
            body=body,
            prospect_id=prospect.id,
            available_at=available_at,
            idempotency_key=f"prospecting:{prospect.id}:outreach:v1",
            actor=actor,
            request=request,
        )
        outbound = queued.outbound
        with transaction.atomic():
            locked = Prospect.objects.select_for_update().get(
                id=prospect.id,
                organization_id=prospect.organization_id,
            )
            before_status = locked.status
            locked.status = ProspectStatus.CONTACTED.value
            locked.contacted_at = locked.contacted_at or timezone.now()
            locked.conversation_id = outbound.conversation_id
            locked.contact_id = outbound.contact_id
            locked.touch_count = max(int(locked.touch_count or 0), 1)
            locked.last_touch_at = timezone.now()
            if locked.next_followup_at is None and locked.touch_count < locked.campaign.max_touches:
                locked.next_followup_at = _next_followup_slot(
                    now=locked.last_touch_at,
                    follow_up_count=locked.follow_up_count,
                )
            locked.error_message = ""
            locked.updated_by_id = getattr(actor, "id", None)
            locked.save(
                update_fields=[
                    "status",
                    "contacted_at",
                    "conversation_id",
                    "contact_id",
                    "touch_count",
                    "last_touch_at",
                    "next_followup_at",
                    "error_message",
                    "updated_by_id",
                    "updated_at",
                ]
            )
            _refresh_contacted_count(campaign_id=locked.campaign_id)
            create_outbox_event(
                event_type=events.PROSPECT_OUTREACH_QUEUED,
                organization_id=locked.organization_id,
                payload={
                    "prospect_id": str(locked.id),
                    "campaign_id": str(locked.campaign_id),
                    "outbound_message_id": str(outbound.id),
                    "conversation_id": str(outbound.conversation_id or ""),
                },
            )
            audit_event_create(
                event_type="prospect_outreach_queued",
                actor=actor,
                organization=_org_stub(locked.organization_id),
                request=request,
                resource_type="prospecting_prospect",
                resource_id=str(locked.id),
                changes={"status": {"before": before_status, "after": locked.status}},
                metadata={"outbound_message_id": str(outbound.id)},
            )
            return OutreachAttempt(prospect=locked, queued=True, reason="")

    @staticmethod
    def queue_generated_message(
        *,
        prospect: Prospect,
        body: str,
        kind: str,
        idempotency_key: str,
        conversation=None,
        contact=None,
        actor=None,
        request=None,
        now=None,
        jitter_seconds: int | None = None,
        count_followup: bool = False,
        schedule_followup: bool = True,
    ) -> OutreachAttempt:
        """Queue a generated reply/follow-up using the same outbound guardrails."""
        prospect = Prospect.objects.select_related("campaign").get(
            id=prospect.id,
            organization_id=prospect.organization_id,
        )
        allowed, reason = _can_send_generated(prospect)
        if not allowed:
            return OutreachAttempt(prospect=prospect, queued=False, reason=reason)

        daily_used = _daily_outbound_count(prospect.campaign)
        if daily_used >= prospect.campaign.daily_cap:
            return OutreachAttempt(prospect=prospect, queued=False, reason="daily_cap_reached")

        body = (body or "").strip()
        if not body:
            return OutreachAttempt(prospect=prospect, queued=False, reason="empty_body")

        available_at = _next_business_slot(now=now, jitter_seconds=jitter_seconds)
        queued = WhatsAppOutboundQueueService.enqueue(
            organization=_org_stub(prospect.organization_id),
            phone=prospect.phone,
            body=body,
            prospect_id=prospect.id,
            conversation=conversation,
            contact=contact,
            available_at=available_at,
            idempotency_key=idempotency_key,
            actor=actor,
            request=request,
        )
        outbound = queued.outbound
        if not queued.created:
            return OutreachAttempt(prospect=prospect, queued=False, reason="duplicate")

        with transaction.atomic():
            locked = Prospect.objects.select_for_update().get(
                id=prospect.id,
                organization_id=prospect.organization_id,
            )
            before_status = locked.status
            if locked.status not in (
                ProspectStatus.INTERESTED.value,
                ProspectStatus.REPLIED.value,
            ):
                locked.status = ProspectStatus.CONTACTED.value
            locked.contacted_at = locked.contacted_at or timezone.now()
            locked.conversation_id = outbound.conversation_id
            locked.contact_id = outbound.contact_id
            locked.touch_count = int(locked.touch_count or 0) + 1
            if count_followup:
                locked.follow_up_count = int(locked.follow_up_count or 0) + 1
            locked.last_touch_at = timezone.now()
            if schedule_followup and locked.touch_count < locked.campaign.max_touches:
                locked.next_followup_at = _next_followup_slot(
                    now=locked.last_touch_at,
                    follow_up_count=locked.follow_up_count,
                )
            else:
                locked.next_followup_at = None
            locked.error_message = ""
            locked.updated_by_id = getattr(actor, "id", None)
            locked.save(
                update_fields=[
                    "status",
                    "contacted_at",
                    "conversation_id",
                    "contact_id",
                    "touch_count",
                    "follow_up_count",
                    "last_touch_at",
                    "next_followup_at",
                    "error_message",
                    "updated_by_id",
                    "updated_at",
                ]
            )
            _refresh_contacted_count(campaign_id=locked.campaign_id)
            create_outbox_event(
                event_type=events.PROSPECT_OUTREACH_QUEUED,
                organization_id=locked.organization_id,
                payload={
                    "prospect_id": str(locked.id),
                    "campaign_id": str(locked.campaign_id),
                    "outbound_message_id": str(outbound.id),
                    "conversation_id": str(outbound.conversation_id or ""),
                    "kind": kind,
                },
            )
            audit_event_create(
                event_type="prospect_outreach_queued",
                actor=actor,
                organization=_org_stub(locked.organization_id),
                request=request,
                resource_type="prospecting_prospect",
                resource_id=str(locked.id),
                changes={"status": {"before": before_status, "after": locked.status}},
                metadata={"outbound_message_id": str(outbound.id), "kind": kind},
            )
            return OutreachAttempt(prospect=locked, queued=True, reason="")


def _eligible_prospects(campaign: ProspectingCampaign):
    qs = Prospect.objects.filter(organization_id=campaign.organization_id, campaign=campaign)
    if campaign.auto_contact:
        qs = qs.filter(
            Q(status=ProspectStatus.APPROVED.value)
            | Q(
                status=ProspectStatus.QUALIFIED.value,
                fit_score__gte=campaign.min_fit_score,
            )
        )
    else:
        qs = qs.filter(status=ProspectStatus.APPROVED.value)
    return qs.order_by("-fit_score", "created_at")


def _can_contact(prospect: Prospect) -> tuple[bool, str]:
    campaign = prospect.campaign
    if campaign.status != CampaignStatus.ACTIVE.value:
        return False, "campaign_not_active"
    if not prospect.phone:
        return False, "missing_phone"
    if prospect.status == ProspectStatus.DO_NOT_CONTACT.value:
        return False, "do_not_contact"
    if prospect.contacted_at:
        return False, "already_contacted"
    if OutboundMessage.objects.filter(
        organization_id=prospect.organization_id,
        prospect_id=prospect.id,
    ).exists():
        return False, "already_queued"
    if not _status_allows_contact(prospect):
        return False, "status_not_allowed"
    if _phone_in_no_contact_list(prospect):
        return False, "no_contact_list"
    if _phone_has_opted_out(prospect):
        return False, "contact_opted_out"
    return True, ""


def _can_send_generated(prospect: Prospect) -> tuple[bool, str]:
    campaign = prospect.campaign
    if campaign.status != CampaignStatus.ACTIVE.value:
        return False, "campaign_not_active"
    if not prospect.phone:
        return False, "missing_phone"
    if prospect.status in (
        ProspectStatus.DO_NOT_CONTACT.value,
        ProspectStatus.NOT_INTERESTED.value,
        ProspectStatus.DISQUALIFIED.value,
        ProspectStatus.FAILED.value,
    ):
        return False, "status_not_allowed"
    if _phone_in_no_contact_list(prospect):
        return False, "no_contact_list"
    if _phone_has_opted_out(prospect):
        return False, "contact_opted_out"
    return True, ""


def _status_allows_contact(prospect: Prospect) -> bool:
    campaign = prospect.campaign
    if prospect.status == ProspectStatus.APPROVED.value:
        return True
    return (
        campaign.auto_contact
        and prospect.status == ProspectStatus.QUALIFIED.value
        and (prospect.fit_score or 0) >= campaign.min_fit_score
    )


def _phone_in_no_contact_list(prospect: Prospect) -> bool:
    blocked = prospect.campaign.metadata.get("do_not_contact_phones", [])
    blocked_digits = {_digits(phone) for phone in blocked}
    return _digits(prospect.phone) in blocked_digits


def _phone_has_opted_out(prospect: Prospect) -> bool:
    resolved = ContactResolver.resolve_by_phone(
        organization=_org_stub(prospect.organization_id),
        raw_phone=prospect.phone,
        create=False,
    )
    contact = resolved.contact
    if contact is None:
        return False
    return contact.status == ContactStatus.BLOCKED.value or bool(
        (contact.metadata or {}).get("prospecting_opted_out_at")
    )


def _daily_outbound_count(campaign: ProspectingCampaign) -> int:
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return OutboundMessage.objects.filter(
        organization_id=campaign.organization_id,
        prospect_id__in=Prospect.objects.filter(campaign=campaign).values("id"),
        created_at__gte=start,
    ).count()


def _next_business_slot(*, now=None, jitter_seconds: int | None = None):
    local_now = timezone.localtime(now or timezone.now())
    jitter = (
        random.randint(0, DEFAULT_JITTER_MAX_SECONDS)
        if jitter_seconds is None
        else max(0, int(jitter_seconds))
    )
    if BUSINESS_START <= local_now.time() < BUSINESS_END:
        base = local_now
    else:
        base = local_now.replace(
            hour=BUSINESS_START.hour,
            minute=BUSINESS_START.minute,
            second=0,
            microsecond=0,
        )
        if local_now.time() >= BUSINESS_END:
            base = base + timedelta(days=1)
    return base + timedelta(seconds=jitter)


def _next_followup_slot(*, now=None, follow_up_count: int = 0):
    index = max(0, min(int(follow_up_count or 0), len(FOLLOW_UP_DELAYS_DAYS) - 1))
    return (now or timezone.now()) + timedelta(days=FOLLOW_UP_DELAYS_DAYS[index])


def _mark_failed(*, prospect: Prospect, reason: str, actor=None, request=None) -> None:
    with transaction.atomic():
        locked = Prospect.objects.select_for_update().get(
            id=prospect.id,
            organization_id=prospect.organization_id,
        )
        before_status = locked.status
        locked.status = ProspectStatus.FAILED.value
        locked.error_message = str(reason)[:500]
        locked.updated_by_id = getattr(actor, "id", None)
        locked.save(update_fields=["status", "error_message", "updated_by_id", "updated_at"])
        audit_event_create(
            event_type="prospect_outreach_failed",
            actor=actor,
            organization=_org_stub(locked.organization_id),
            request=request,
            resource_type="prospecting_prospect",
            resource_id=str(locked.id),
            changes={"status": {"before": before_status, "after": locked.status}},
            metadata={"reason": locked.error_message},
        )


def _refresh_contacted_count(*, campaign_id) -> None:
    count = Prospect.objects.filter(
        campaign_id=campaign_id,
        status__in=CONTACTED_STATUSES,
        deleted_at__isnull=True,
    ).count()
    ProspectingCampaign.objects.filter(id=campaign_id).update(
        contacted_count=count,
        updated_at=timezone.now(),
    )


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _org_stub(organization_id):
    from crm.organizations.models import Organization

    return Organization.objects.get(id=organization_id)
