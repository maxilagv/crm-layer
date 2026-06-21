"""Prospecting email persistence and Resend delivery."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core import signing
from django.db import IntegrityError, transaction
from django.utils import timezone

from crm.ai.services.ai_gateway import AIGateway
from crm.prospecting.models import Prospect, ProspectEmailMessage

from .resend_client import ResendEmailClient

_UNSUBSCRIBE_SALT = "crm.prospecting.email.unsubscribe"


@dataclass(frozen=True)
class EmailDeliveryAttempt:
    message: ProspectEmailMessage | None
    queued: bool
    sent: bool = False
    reason: str = ""


class ProspectEmailSender:
    def __init__(self, *, client: ResendEmailClient | None = None):
        self.client = client or ResendEmailClient()

    def draft_and_send_opener(
        self,
        *,
        prospect: Prospect,
        available_at,
        idempotency_key: str,
        actor=None,
        request=None,
    ) -> EmailDeliveryAttempt:
        unsubscribe_url = build_unsubscribe_url(prospect=prospect, request=request)
        unsubscribe_line = (
            f"Si preferis que no vuelva a escribirte, usa este link: {unsubscribe_url}"
        )
        ai = AIGateway.draft_outreach_email(
            prospect_id=prospect.id,
            unsubscribe_line=unsubscribe_line,
            actor=actor,
            metadata={"source": "prospecting_email_outreach"},
            http_request=request,
        )
        if not ai.succeeded or not ai.data:
            return EmailDeliveryAttempt(
                message=None,
                queued=False,
                reason=ai.error_code or ai.error_message or "email_draft_failed",
            )
        subject = str(ai.data.get("subject") or "").strip()
        body = str(ai.data.get("body") or "").strip()
        if not subject or not body:
            return EmailDeliveryAttempt(message=None, queued=False, reason="empty_email_draft")
        return self.queue_or_send(
            prospect=prospect,
            subject=subject,
            body=body,
            available_at=available_at,
            idempotency_key=idempotency_key,
            unsubscribe_url=unsubscribe_url,
            unsubscribe_line=unsubscribe_line,
        )

    def queue_or_send(
        self,
        *,
        prospect: Prospect,
        subject: str,
        body: str,
        available_at,
        idempotency_key: str,
        unsubscribe_url: str | None = None,
        unsubscribe_line: str | None = None,
    ) -> EmailDeliveryAttempt:
        unsubscribe_url = unsubscribe_url or build_unsubscribe_url(prospect=prospect)
        unsubscribe_line = unsubscribe_line or (
            f"Si preferis que no vuelva a escribirte, usa este link: {unsubscribe_url}"
        )
        body = _ensure_footer(body, unsubscribe_line=unsubscribe_line)
        try:
            with transaction.atomic():
                message, created = ProspectEmailMessage.objects.get_or_create(
                    organization_id=prospect.organization_id,
                    idempotency_key=idempotency_key,
                    defaults={
                        "prospect": prospect,
                        "campaign": prospect.campaign,
                        "to_email": prospect.owner_email,
                        "subject": subject[:255],
                        "body": body,
                        "available_at": available_at,
                    },
                )
        except IntegrityError:
            message = ProspectEmailMessage.objects.filter(
                organization_id=prospect.organization_id,
                idempotency_key=idempotency_key,
            ).first()
            return EmailDeliveryAttempt(message=message, queued=False, reason="duplicate")

        if not created:
            return EmailDeliveryAttempt(message=message, queued=False, reason="duplicate")
        if message.available_at > timezone.now():
            return EmailDeliveryAttempt(message=message, queued=True, reason="scheduled")
        return self._send_message(message=message, unsubscribe_url=unsubscribe_url)

    def send_due(self, *, limit: int = 100) -> int:
        sent = 0
        qs = (
            ProspectEmailMessage.objects.select_related("prospect", "campaign")
            .filter(status=ProspectEmailMessage.Status.QUEUED, available_at__lte=timezone.now())
            .order_by("available_at")[: max(1, min(limit, 500))]
        )
        for message in qs:
            attempt = self._send_message(
                message=message,
                unsubscribe_url=build_unsubscribe_url(prospect=message.prospect),
            )
            if attempt.sent:
                sent += 1
        return sent

    def _send_message(
        self,
        *,
        message: ProspectEmailMessage,
        unsubscribe_url: str,
    ) -> EmailDeliveryAttempt:
        result = self.client.send(
            to_email=message.to_email,
            subject=message.subject,
            body=message.body,
            headers={
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        )
        if result.get("sent"):
            message.status = ProspectEmailMessage.Status.SENT
            message.provider_message_id = str(result.get("message_id") or "")
            message.sent_at = timezone.now()
            message.error_message = ""
            message.save(
                update_fields=[
                    "status",
                    "provider_message_id",
                    "sent_at",
                    "error_message",
                    "updated_at",
                ]
            )
            return EmailDeliveryAttempt(message=message, queued=True, sent=True)

        message.status = ProspectEmailMessage.Status.FAILED
        message.error_message = str(result.get("error") or "email_send_failed")[:2000]
        message.save(update_fields=["status", "error_message", "updated_at"])
        return EmailDeliveryAttempt(message=message, queued=False, reason=message.error_message)


def build_unsubscribe_url(*, prospect: Prospect, request=None) -> str:
    token = signing.dumps(
        {
            "prospect_id": str(prospect.id),
            "organization_id": str(prospect.organization_id),
            "email": prospect.owner_email,
        },
        salt=_UNSUBSCRIBE_SALT,
    )
    path = f"/api/v1/prospecting/unsubscribe/{token}/"
    if request is not None:
        return request.build_absolute_uri(path)
    return f"{str(getattr(settings, 'PUBLIC_APP_URL', '')).rstrip('/')}{path}"


def load_unsubscribe_token(token: str) -> dict:
    data = signing.loads(token, salt=_UNSUBSCRIBE_SALT)
    return data if isinstance(data, dict) else {}


def _ensure_footer(body: str, *, unsubscribe_line: str) -> str:
    body = (body or "").strip()
    parts = [body]
    if unsubscribe_line and unsubscribe_line not in body:
        parts.append(unsubscribe_line)
    address = str(getattr(settings, "PROSPECTING_EMAIL_FOOTER_ADDRESS", "") or "").strip()
    if address and address not in body:
        parts.append(address)
    return "\n\n".join(part for part in parts if part).strip()
