"""Interpret inbound replies from Cazador prospects."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from crm.ai.services.ai_gateway import AIGateway
from crm.audit.services import audit_event_create
from crm.contacts.constants import ContactStatus
from crm.core.services.outbox import create_outbox_event
from crm.leads.domain.enums import LeadSourceType
from crm.leads.services.lead_creation import create_manual_lead
from crm.notifications.domain.enums import NotificationPriority, NotificationType
from crm.notifications.services.notification_service import NotificationService
from crm.prospecting.domain import events
from crm.prospecting.domain.enums import ProspectStatus
from crm.prospecting.models import Prospect, ProspectingCampaign
from crm.prospecting.services.conversation_engine import handle_inbound_next_step
from crm.whatsapp.models import OutboundMessage

OPT_OUT_KEYWORDS = (
    "no",
    "baja",
    "no me escriban",
    "no quiero",
    "sacame",
    "eliminar",
    "unsubscribe",
)


@dataclass(frozen=True)
class ReplyInterpretation:
    prospect: Prospect
    intent: str
    confidence: float
    lead_id: str | None = None
    opted_out: bool = False
    next_action: str = "none"
    objection_type: str = ""
    response_queued: bool = False
    owner_notified: bool = False


class ProspectReplyInterpreter:
    @staticmethod
    def interpret_inbound(
        *,
        organization,
        conversation,
        contact,
        message,
        actor=None,
        request=None,
    ) -> ReplyInterpretation | None:
        prospect = _find_prospect(
            organization=organization,
            conversation=conversation,
            contact=contact,
        )
        if prospect is None:
            return None

        message_id = str(message.id)
        if _message_was_interpreted(prospect, message_id):
            return ReplyInterpretation(
                prospect=prospect,
                intent=_intent_for_status(prospect.status),
                confidence=0.0,
            )
        if not cache.add(f"prospecting:reply-interpret:{message_id}", 1, timeout=900):
            return ReplyInterpretation(
                prospect=prospect,
                intent=_intent_for_status(prospect.status),
                confidence=0.0,
            )

        body = message.body or ""
        opted_out = _is_opt_out(body)
        if opted_out:
            data = {
                "intent": "do_not_contact",
                "confidence": 1.0,
                "reasoning": "Opt-out keyword detected before AI classification.",
            }
            ai_run_id = None
        else:
            outbound_body = _latest_outbound_body(prospect)
            ai = AIGateway.classify_prospect_reply(
                prospect_id=prospect.id,
                conversation_id=conversation.id,
                message_id=message.id,
                outbound_message=outbound_body,
                actor=actor,
                metadata={"source": "prospecting_reply_interpretation"},
                http_request=request,
            )
            if not ai.succeeded or not ai.data:
                # Transient AI failure: don't silently drop the reply. Mark it REPLIED so the
                # prospect surfaces in the queue for manual handling instead of going stale.
                data = {
                    "intent": "unclear",
                    "confidence": 0.0,
                    "reasoning": f"AI classification failed: {ai.error_code or 'unknown'}",
                }
            else:
                data = ai.data
            ai_run_id = ai.run_id

        intent = str(data.get("intent") or "unclear")
        next_action = str(data.get("next_action") or "none")
        objection_type = str(data.get("objection_type") or "")
        status = _status_for_intent(intent)
        lead_id = None
        locked = prospect
        with transaction.atomic():
            locked = Prospect.objects.select_for_update().get(
                id=prospect.id,
                organization_id=organization.id,
            )
            before_status = locked.status
            locked.status = status
            locked.replied_at = timezone.now()
            locked.contact_id = contact.id
            locked.conversation_id = conversation.id
            locked.ai_run_id = ai_run_id or locked.ai_run_id
            locked.updated_by_id = getattr(actor, "id", None)
            _mark_message_interpreted(
                prospect=locked,
                message_id=message_id,
                intent=intent,
                next_action=next_action,
                objection_type=objection_type,
            )
            fields = [
                "status",
                "replied_at",
                "contact_id",
                "conversation_id",
                "ai_run_id",
                "updated_by_id",
                "metadata",
                "updated_at",
            ]
            if status == ProspectStatus.DO_NOT_CONTACT.value:
                _suppress_contact(contact)
            if status == ProspectStatus.INTERESTED.value:
                creation = create_manual_lead(
                    organization=organization,
                    contact=contact,
                    actor=actor,
                    request=request,
                    source_type=LeadSourceType.CAMPAIGN.value,
                    metadata={
                        "prospect_id": str(locked.id),
                        "campaign_id": str(locked.campaign_id),
                    },
                )
                if creation.lead is not None:
                    locked.lead_id = creation.lead.id
                    lead_id = str(creation.lead.id)
                    fields.append("lead_id")
                _notify_owner(organization=organization, prospect=locked, lead_id=lead_id)
            locked.save(update_fields=fields)
            _refresh_interested_count(campaign_id=locked.campaign_id)
            create_outbox_event(
                event_type=events.PROSPECT_REPLY_INTERPRETED,
                organization_id=organization.id,
                payload={
                    "prospect_id": str(locked.id),
                    "campaign_id": str(locked.campaign_id),
                    "intent": intent,
                    "status": locked.status,
                    "message_id": str(message.id),
                },
            )
            if locked.status == ProspectStatus.INTERESTED.value:
                create_outbox_event(
                    event_type=events.PROSPECT_INTERESTED,
                    organization_id=organization.id,
                    payload={
                        "prospect_id": str(locked.id),
                        "campaign_id": str(locked.campaign_id),
                        "lead_id": lead_id,
                    },
                )
            audit_event_create(
                event_type="prospect_reply_interpreted",
                actor=actor,
                organization=organization,
                request=request,
                resource_type="prospecting_prospect",
                resource_id=str(locked.id),
                changes={"status": {"before": before_status, "after": locked.status}},
                metadata={"intent": intent, "confidence": data.get("confidence", 0)},
            )

        action = None
        if not opted_out:
            action = handle_inbound_next_step(
                organization=organization,
                prospect=locked,
                conversation=conversation,
                contact=contact,
                message=message,
                intent=intent,
                next_action=next_action,
                objection_type=objection_type,
                actor=actor,
                request=request,
            )

        return ReplyInterpretation(
            prospect=locked,
            intent=intent,
            confidence=float(data.get("confidence", 0)),
            lead_id=lead_id,
            opted_out=opted_out,
            next_action=next_action,
            objection_type=objection_type,
            response_queued=bool(action and action.queued),
            owner_notified=bool(action and action.notified),
        )


def _find_prospect(*, organization, conversation, contact) -> Prospect | None:
    qs = Prospect.objects.filter(organization_id=organization.id)
    prospect = qs.filter(conversation_id=conversation.id).order_by("-contacted_at").first()
    if prospect is not None:
        return prospect
    prospect = qs.filter(contact_id=contact.id).order_by("-contacted_at", "-created_at").first()
    if prospect is not None:
        return prospect
    if getattr(contact, "source", "") == "prospecting":
        phones = list(contact.phones.values_list("phone_e164", flat=True))
        return qs.filter(phone__in=phones).first()
    return None


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


def _status_for_intent(intent: str) -> str:
    if intent == "interested":
        return ProspectStatus.INTERESTED.value
    if intent == "not_interested":
        return ProspectStatus.NOT_INTERESTED.value
    if intent == "do_not_contact":
        return ProspectStatus.DO_NOT_CONTACT.value
    return ProspectStatus.REPLIED.value


def _intent_for_status(status: str) -> str:
    if status == ProspectStatus.INTERESTED.value:
        return "interested"
    if status == ProspectStatus.NOT_INTERESTED.value:
        return "not_interested"
    if status == ProspectStatus.DO_NOT_CONTACT.value:
        return "do_not_contact"
    return "unclear"


def _message_was_interpreted(prospect: Prospect, message_id: str) -> bool:
    interpreted = (prospect.metadata or {}).get("prospecting_interpreted_message_ids") or []
    return str(message_id) in {str(item) for item in interpreted}


def _mark_message_interpreted(
    *,
    prospect: Prospect,
    message_id: str,
    intent: str,
    next_action: str,
    objection_type: str,
) -> None:
    metadata = dict(prospect.metadata or {})
    interpreted = [str(item) for item in metadata.get("prospecting_interpreted_message_ids") or []]
    if str(message_id) not in interpreted:
        interpreted.append(str(message_id))
    metadata["prospecting_interpreted_message_ids"] = interpreted[-50:]
    by_message = dict(metadata.get("prospecting_reply_interpretations") or {})
    by_message[str(message_id)] = {
        "intent": intent,
        "next_action": next_action,
        "objection_type": objection_type,
        "at": timezone.now().isoformat(),
    }
    metadata["prospecting_reply_interpretations"] = by_message
    prospect.metadata = metadata


def _suppress_contact(contact) -> None:
    metadata = dict(contact.metadata or {})
    metadata["prospecting_opted_out_at"] = timezone.now().isoformat()
    contact.metadata = metadata
    contact.status = ContactStatus.BLOCKED.value
    contact.save(update_fields=["metadata", "status", "updated_at"])


def _notify_owner(*, organization, prospect: Prospect, lead_id: str | None) -> None:
    NotificationService.notify_owner(
        organization=organization,
        notification_type=NotificationType.HOT_LEAD.value,
        title=f"Prospecto interesado: {prospect.business_name}",
        body=(
            f"{prospect.business_name} respondio con interes a la campana {prospect.campaign.name}."
        ),
        priority=NotificationPriority.HIGH.value,
        resource_type="prospecting_prospect",
        resource_id=prospect.id,
        metadata={"lead_id": lead_id or "", "campaign_id": str(prospect.campaign_id)},
        deduplication_key=f"prospecting-interested:{prospect.id}",
    )


def _refresh_interested_count(*, campaign_id) -> None:
    count = Prospect.objects.filter(
        campaign_id=campaign_id,
        status=ProspectStatus.INTERESTED.value,
        deleted_at__isnull=True,
    ).count()
    ProspectingCampaign.objects.filter(id=campaign_id).update(
        interested_count=count,
        updated_at=timezone.now(),
    )


_OPT_OUT_TOKENS = tuple(k for k in OPT_OUT_KEYWORDS if " " not in k)
_OPT_OUT_PHRASES = tuple(k for k in OPT_OUT_KEYWORDS if " " in k)
_OPT_OUT_TOKEN_RE = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in _OPT_OUT_TOKENS) + r")\b")
# Only treat a keyword hit as opt-out in short, standalone replies; longer nuanced
# messages ("no quiero perder la oportunidad", "estamos en planta baja") go to the AI.
_MAX_OPT_OUT_WORDS = 6


def _is_opt_out(text: str) -> bool:
    normalized = _normalize(text)
    if not normalized:
        return False
    if normalized in OPT_OUT_KEYWORDS:
        return True
    if len(normalized.split()) > _MAX_OPT_OUT_WORDS:
        return False
    if any(phrase in normalized for phrase in _OPT_OUT_PHRASES):
        return True
    return bool(_OPT_OUT_TOKEN_RE.search(normalized))


def _normalize(text: str) -> str:
    text = "".join(
        c for c in unicodedata.normalize("NFD", text or "") if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", text.lower()).strip()
