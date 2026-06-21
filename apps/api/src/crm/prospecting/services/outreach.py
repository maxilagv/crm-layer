"""Outbound orchestration for Cazador prospects."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import time, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from crm.ai.services.ai_gateway import AIGateway
from crm.audit.services import audit_event_create
from crm.business_settings.models import ProspectingPolicy
from crm.contacts.constants import ContactStatus
from crm.contacts.models import ContactEmail
from crm.contacts.services import ContactResolver
from crm.core.services.outbox import create_outbox_event
from crm.prospecting.domain import events
from crm.prospecting.domain.enums import (
    CONTACTED_STATUSES,
    CampaignStatus,
    ProspectChannel,
    ProspectStatus,
)
from crm.prospecting.models import Prospect, ProspectEmailMessage, ProspectingCampaign
from crm.prospecting.services.email_sender import ProspectEmailSender
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
            if reason in {"missing_phone", "missing_email"}:
                _mark_failed(prospect=prospect, reason=reason, actor=actor, request=request)
                prospect.refresh_from_db()
            return OutreachAttempt(prospect=prospect, queued=False, reason=reason)

        cap_reason = _daily_cap_block_reason(prospect.campaign)
        if cap_reason:
            return OutreachAttempt(prospect=prospect, queued=False, reason=cap_reason)

        if prospect.campaign.channel == ProspectChannel.EMAIL.value:
            return _contact_prospect_by_email(
                prospect=prospect,
                actor=actor,
                request=request,
                now=now,
                jitter_seconds=jitter_seconds,
            )

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
        available_at = _next_business_slot(
            organization_id=prospect.organization_id,
            now=now,
            jitter_seconds=jitter_seconds,
        )
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

        cap_reason = _daily_cap_block_reason(prospect.campaign)
        if cap_reason:
            return OutreachAttempt(prospect=prospect, queued=False, reason=cap_reason)

        body = (body or "").strip()
        if not body:
            return OutreachAttempt(prospect=prospect, queued=False, reason="empty_body")

        if prospect.campaign.channel == ProspectChannel.EMAIL.value:
            return _queue_generated_email(
                prospect=prospect,
                body=body,
                kind=kind,
                idempotency_key=idempotency_key,
                actor=actor,
                request=request,
                now=now,
                jitter_seconds=jitter_seconds,
                count_followup=count_followup,
                schedule_followup=schedule_followup,
            )

        available_at = _next_business_slot(
            organization_id=prospect.organization_id,
            now=now,
            jitter_seconds=jitter_seconds,
        )
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


def _contact_prospect_by_email(
    *,
    prospect: Prospect,
    actor=None,
    request=None,
    now=None,
    jitter_seconds: int | None = None,
) -> OutreachAttempt:
    available_at = _next_business_slot(
        organization_id=prospect.organization_id,
        now=now,
        jitter_seconds=jitter_seconds,
    )
    attempt = ProspectEmailSender().draft_and_send_opener(
        prospect=prospect,
        available_at=available_at,
        idempotency_key=f"prospecting:{prospect.id}:email:v1",
        actor=actor,
        request=request,
    )
    if not attempt.queued or attempt.message is None:
        _mark_failed(
            prospect=prospect,
            reason=attempt.reason or "email_send_failed",
            actor=actor,
            request=request,
        )
        prospect.refresh_from_db()
        return OutreachAttempt(prospect=prospect, queued=False, reason=attempt.reason)
    return _mark_email_contacted(
        prospect=prospect,
        email_message=attempt.message,
        kind="outreach",
        actor=actor,
        request=request,
    )


def _queue_generated_email(
    *,
    prospect: Prospect,
    body: str,
    kind: str,
    idempotency_key: str,
    actor=None,
    request=None,
    now=None,
    jitter_seconds: int | None = None,
    count_followup: bool = False,
    schedule_followup: bool = True,
) -> OutreachAttempt:
    available_at = _next_business_slot(
        organization_id=prospect.organization_id,
        now=now,
        jitter_seconds=jitter_seconds,
    )
    attempt = ProspectEmailSender().queue_or_send(
        prospect=prospect,
        subject=_generated_email_subject(prospect=prospect, kind=kind),
        body=body,
        available_at=available_at,
        idempotency_key=idempotency_key,
    )
    if not attempt.queued or attempt.message is None:
        return OutreachAttempt(prospect=prospect, queued=False, reason=attempt.reason)
    return _mark_email_contacted(
        prospect=prospect,
        email_message=attempt.message,
        kind=kind,
        actor=actor,
        request=request,
        count_followup=count_followup,
        schedule_followup=schedule_followup,
    )


def _mark_email_contacted(
    *,
    prospect: Prospect,
    email_message: ProspectEmailMessage,
    kind: str,
    actor=None,
    request=None,
    count_followup: bool = False,
    schedule_followup: bool = True,
) -> OutreachAttempt:
    with transaction.atomic():
        locked = Prospect.objects.select_for_update().get(
            id=prospect.id,
            organization_id=prospect.organization_id,
        )
        before_status = locked.status
        if locked.status not in (ProspectStatus.INTERESTED.value, ProspectStatus.REPLIED.value):
            locked.status = ProspectStatus.CONTACTED.value
        locked.contacted_at = locked.contacted_at or timezone.now()
        locked.touch_count = int(locked.touch_count or 0) + 1
        if kind == "outreach":
            locked.touch_count = max(locked.touch_count, 1)
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
                "email_message_id": str(email_message.id),
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
            metadata={"email_message_id": str(email_message.id), "kind": kind},
        )
        return OutreachAttempt(prospect=locked, queued=True, reason="")


def _generated_email_subject(*, prospect: Prospect, kind: str) -> str:
    if kind == "followup":
        return "Seguimos con la idea para tu negocio"
    if kind == "reply":
        return f"Respuesta para {prospect.business_name}"[:120]
    return "Idea para tu presencia online"


def _can_contact(prospect: Prospect) -> tuple[bool, str]:
    campaign = prospect.campaign
    if campaign.status != CampaignStatus.ACTIVE.value:
        return False, "campaign_not_active"
    if _agent_paused(prospect.organization_id):
        return False, "agent_paused"
    if prospect.status == ProspectStatus.DO_NOT_CONTACT.value:
        return False, "do_not_contact"
    if prospect.contacted_at:
        return False, "already_contacted"
    if campaign.channel == ProspectChannel.EMAIL.value:
        if not prospect.owner_email:
            return False, "missing_email"
        if ProspectEmailMessage.objects.filter(
            organization_id=prospect.organization_id,
            prospect_id=prospect.id,
        ).exists():
            return False, "already_queued"
        if not _status_allows_contact(prospect):
            return False, "status_not_allowed"
        if _email_in_no_contact_list(prospect):
            return False, "no_contact_list"
        if _email_has_opted_out(prospect):
            return False, "contact_opted_out"
        return True, ""
    if not prospect.phone:
        return False, "missing_phone"
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
    if _agent_paused(prospect.organization_id):
        return False, "agent_paused"
    if campaign.channel == ProspectChannel.EMAIL.value and not prospect.owner_email:
        return False, "missing_email"
    if campaign.channel != ProspectChannel.EMAIL.value and not prospect.phone:
        return False, "missing_phone"
    if prospect.status in (
        ProspectStatus.DO_NOT_CONTACT.value,
        ProspectStatus.NOT_INTERESTED.value,
        ProspectStatus.DISQUALIFIED.value,
        ProspectStatus.FAILED.value,
    ):
        return False, "status_not_allowed"
    if campaign.channel == ProspectChannel.EMAIL.value:
        if _email_in_no_contact_list(prospect):
            return False, "no_contact_list"
        if _email_has_opted_out(prospect):
            return False, "contact_opted_out"
        return True, ""
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


def _email_in_no_contact_list(prospect: Prospect) -> bool:
    blocked = prospect.campaign.metadata.get("do_not_contact_emails", [])
    return _normalize_email(prospect.owner_email) in {_normalize_email(email) for email in blocked}


def _email_has_opted_out(prospect: Prospect) -> bool:
    if (prospect.metadata or {}).get("prospecting_opted_out_at"):
        return True
    email = _normalize_email(prospect.owner_email)
    if not email:
        return False
    linked = (
        ContactEmail.objects.filter(
            organization_id=prospect.organization_id,
            normalized_email=email,
        )
        .select_related("contact")
        .first()
    )
    if linked is None:
        return False
    contact = linked.contact
    return contact.status == ContactStatus.BLOCKED.value or bool(
        (contact.metadata or {}).get("prospecting_opted_out_at")
    )


def _daily_outbound_count(campaign: ProspectingCampaign) -> int:
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    whatsapp_count = OutboundMessage.objects.filter(
        organization_id=campaign.organization_id,
        prospect_id__in=Prospect.objects.filter(campaign=campaign).values("id"),
        created_at__gte=start,
    ).count()
    email_count = ProspectEmailMessage.objects.filter(
        organization_id=campaign.organization_id,
        campaign=campaign,
        created_at__gte=start,
    ).count()
    return whatsapp_count + email_count


def _daily_email_count(campaign: ProspectingCampaign) -> int:
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return ProspectEmailMessage.objects.filter(
        organization_id=campaign.organization_id,
        campaign=campaign,
        created_at__gte=start,
    ).count()


def _org_daily_outbound_count(organization_id) -> int:
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    whatsapp_count = OutboundMessage.objects.filter(
        organization_id=organization_id,
        prospect_id__isnull=False,
        created_at__gte=start,
    ).count()
    email_count = ProspectEmailMessage.objects.filter(
        organization_id=organization_id,
        created_at__gte=start,
    ).count()
    return whatsapp_count + email_count


def _daily_cap_block_reason(campaign: ProspectingCampaign) -> str:
    if _daily_outbound_count(campaign) >= int(campaign.daily_cap or 0):
        return "daily_cap_reached"
    email_daily_cap = int(getattr(settings, "PROSPECTING_EMAIL_DAILY_CAP", 50))
    if (
        campaign.channel == ProspectChannel.EMAIL.value
        and _daily_email_count(campaign) >= email_daily_cap
    ):
        return "email_daily_cap_reached"
    policy = _prospecting_policy(campaign.organization_id)
    org_count = _org_daily_outbound_count(campaign.organization_id)
    if policy.org_daily_cap is not None and org_count >= int(policy.org_daily_cap):
        return "org_daily_cap_reached"
    return ""


def _prospecting_policy(organization_id) -> ProspectingPolicy:
    policy = ProspectingPolicy.objects.filter(organization_id=organization_id).first()
    if policy is not None:
        return policy
    return ProspectingPolicy(organization_id=organization_id)


def _agent_paused(organization_id) -> bool:
    return bool(_prospecting_policy(organization_id).agent_paused)


def _send_window_reason(organization_id, *, now=None) -> str:
    return "" if _is_within_send_window(organization_id, now=now) else "outside_send_window"


def _is_within_send_window(organization_id, *, now=None) -> bool:
    policy = _prospecting_policy(organization_id)
    local_now = timezone.localtime(now or timezone.now())
    start = time(_configured_hour(policy.send_start_hour, BUSINESS_START.hour), 0)
    cutoff = time(_configured_hour(policy.send_cutoff_hour, BUSINESS_END.hour), 0)
    return start <= local_now.time() < cutoff


def _next_business_slot(*, organization_id=None, now=None, jitter_seconds: int | None = None):
    local_now = timezone.localtime(now or timezone.now())
    policy = _prospecting_policy(organization_id) if organization_id else None
    start_hour = _configured_hour(getattr(policy, "send_start_hour", None), BUSINESS_START.hour)
    cutoff_hour = _configured_hour(getattr(policy, "send_cutoff_hour", None), BUSINESS_END.hour)
    start = time(start_hour, 0)
    cutoff = time(cutoff_hour, 0)
    jitter = (
        random.randint(0, DEFAULT_JITTER_MAX_SECONDS)
        if jitter_seconds is None
        else max(0, int(jitter_seconds))
    )
    if start <= local_now.time() < cutoff:
        base = local_now
    else:
        base = local_now.replace(
            hour=start.hour,
            minute=start.minute,
            second=0,
            microsecond=0,
        )
        if local_now.time() >= cutoff:
            base = base + timedelta(days=1)
    return base + timedelta(seconds=jitter)


def _configured_hour(value, default: int) -> int:
    return default if value is None else int(value)


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


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def _org_stub(organization_id):
    from crm.organizations.models import Organization

    return Organization.objects.get(id=organization_id)
