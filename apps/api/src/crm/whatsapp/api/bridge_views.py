"""Endpoints for the unofficial WhatsApp bridge (whatsapp-web.js).

Temporary, for local testing until the official Meta Cloud API is available.

- ``inbound``: the bridge posts an incoming message; we resolve contact +
  conversation, ingest it, run the AI agent (sales/support by mode) and return
  the reply for the bridge to send.
- ``event``: the bridge reports QR / connection status; we cache it per org.
- ``status``: the dashboard reads the cached QR + connection state.

Bridge-facing endpoints authenticate with a shared secret header
(``X-Bridge-Secret``), not a user JWT.
"""

import re
import unicodedata

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from crm.business_settings.models import BusinessProfile
from crm.contacts.constants import ContactType
from crm.conversations.constants import (
    ACTIVE_STATUSES,
    Channel,
    ConversationMode,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from crm.conversations.services import MessageIngestionService
from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.organizations.models import Organization
from crm.organizations.selectors.organizations import resolve_current_organization

CACHE_TTL = 3600
_ACTIVE = [s.value for s in ACTIVE_STATUSES]
_AI_MODES = {
    ConversationMode.SALES_AI.value,
    ConversationMode.SUPPORT_AI.value,
    ConversationMode.INTERNAL_ASSISTANT.value,
}

# Owner-only chat commands -> (document type, output format). The owner can
# write e.g. "/propuesta para ACME: app de turnos, 3 meses de soporte" and gets
# the generated file back through the bridge.
DOC_COMMANDS: dict[str, tuple[str, str]] = {
    "/propuesta": ("proposal", "pdf"),
    "/presupuesto": ("quote", "pdf"),
    "/cotizacion": ("quote", "pdf"),
    "/excel": ("quote", "xlsx"),
    "/informe": ("report", "pdf"),
    "/reporte": ("report", "pdf"),
    "/deck": ("deck", "pptx"),
    "/presentacion": ("deck", "pptx"),
    "/ppt": ("deck", "pptx"),
    "/powerpoint": ("deck", "pptx"),
    "/pdf": ("proposal", "pdf"),
}


def _cache_key(organization_id) -> str:
    return f"wa_bridge:{organization_id}"


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _command_token(body: str) -> str:
    """First whitespace-delimited token, lowercased and accent-stripped."""
    stripped = (body or "").strip()
    if not stripped:
        return ""
    return _strip_accents(stripped.split(None, 1)[0].lower())


def _is_owner(organization, phone: str) -> bool:
    """True if the phone matches the configured owner number (suffix match).

    Reads the owner number from BusinessProfile.owner_phone, falling back to the
    OWNER_WHATSAPP_NUMBER env var. Suffix match tolerates country-code differences.
    """
    target = _digits(phone)
    if len(target) < 8:
        return False
    profile = BusinessProfile.objects.filter(organization_id=organization.id).first()
    candidates = [
        getattr(profile, "owner_phone", "") or "",
        getattr(settings, "OWNER_WHATSAPP_NUMBER", "") or "",
    ]
    for cand in candidates:
        cd = _digits(cand)
        if len(cd) >= 8 and (target.endswith(cd) or cd.endswith(target)):
            return True
    return False


def _require_secret(request) -> None:
    provided = request.headers.get("X-Bridge-Secret", "")
    expected = getattr(settings, "WA_BRIDGE_SHARED_SECRET", "")
    if not expected or provided != expected:
        raise PermissionDenied("Invalid bridge secret")


def _resolve_org(request) -> Organization:
    org_id = request.data.get("organization_id") or request.query_params.get("organization_id")
    if not org_id:
        raise ValidationError({"organization_id": "requerido"})
    org = Organization.objects.filter(id=org_id).first()
    if org is None:
        raise ValidationError({"organization_id": "organización no encontrada"})
    return org


class WhatsAppBridgeEventView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        _require_secret(request)
        org = _resolve_org(request)
        state = str(request.data.get("type", "unknown"))
        payload = {
            "state": state,
            "qr": request.data.get("qr"),
            "info": request.data.get("info") or {},
            "updated_at": timezone.now().isoformat(),
        }
        # On 'ready'/'authenticated' the QR is consumed; drop it.
        if state in {"ready", "authenticated"}:
            payload["qr"] = None
        cache.set(_cache_key(org.id), payload, CACHE_TTL)
        return success_response(request, {"ok": True})


class WhatsAppBridgeInboundView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        _require_secret(request)
        org = _resolve_org(request)
        phone = str(request.data.get("from", "")).strip()
        body = str(request.data.get("body", "")).strip()
        external_id = str(request.data.get("message_id", "")).strip()
        if not phone or not body:
            raise ValidationError("from y body son requeridos")

        result = MessageIngestionService.ingest(
            organization=org,
            channel=Channel.WHATSAPP,
            direction=MessageDirection.INBOUND,
            phone=phone,
            message_type=MessageType.TEXT,
            body=body,
            external_message_id=external_id,
        )
        conversation = result.conversation
        reply_text = None
        should_send = False
        reason = "manual"
        document = None
        prospect_interpretation = None

        is_owner = _is_owner(org, phone)
        # If the owner writes in, treat them as internal -> personal work assistant.
        if is_owner:
            contact = result.contact
            if contact.type != ContactType.INTERNAL:
                contact.type = ContactType.INTERNAL
                contact.save(update_fields=["type", "updated_at"])
            if conversation.mode != ConversationMode.INTERNAL_ASSISTANT.value:
                conversation.mode = ConversationMode.INTERNAL_ASSISTANT.value
                conversation.save(update_fields=["mode", "updated_at"])
            # Owner dictating work -> turn any explicit task into a card in Tareas.
            # Skip slash commands (those are handled below as document commands).
            if body and not body.startswith("/"):
                self._enqueue_owner_task_extraction(result.message.id)
        else:
            prospect_interpretation = self._interpret_prospect_reply(
                org=org,
                conversation=conversation,
                result=result,
                request=request,
            )

        doc_command = DOC_COMMANDS.get(_command_token(body)) if is_owner else None
        if doc_command is not None:
            # Explicit owner command: draft + generate the document and return its URL.
            doc_type, fmt = doc_command
            reply_text, should_send, reason, document = self._run_document_command(
                org, conversation, result, doc_type=doc_type, fmt=fmt, body=body
            )
        else:
            # A prospect who just opted out (keyword or AI-classified do_not_contact) must
            # NOT get an autonomous reply on this same turn. "do_not_contact" is the value
            # of ProspectStatus.DO_NOT_CONTACT (literal to avoid a whatsapp->prospecting cycle).
            opted_out = bool(
                prospect_interpretation
                and (
                    prospect_interpretation.get("opted_out")
                    or prospect_interpretation.get("status") == "do_not_contact"
                )
            )
            ai_eligible = (
                not opted_out
                and conversation.ai_enabled
                and conversation.status in _ACTIVE
                and conversation.mode in _AI_MODES
            )
            if ai_eligible:
                reply_text, should_send, reason = self._run_agent(org, conversation, result)
            elif opted_out:
                reason = "prospect_opted_out"

        return success_response(
            request,
            {
                "conversation_id": str(conversation.id),
                "contact_id": str(result.contact.id),
                "mode": conversation.mode,
                "should_send": should_send,
                "reply": reply_text,
                "reason": reason,
                "document": document,
                "prospect": prospect_interpretation,
            },
        )

    @staticmethod
    def _enqueue_owner_task_extraction(message_id):
        """Pull explicit owner tasks ("recordame...") into Tareas as cards (best-effort)."""
        try:
            from crm.tasks.tasks import extract_tasks_from_message

            extract_tasks_from_message.delay(message_id=str(message_id), auto_confirm=True)
        except Exception:  # noqa: BLE001 — task extraction must never break the inbound reply
            pass

    @staticmethod
    def _run_agent(org, conversation, result):
        from crm.ai.services.ai_gateway import AIGateway

        try:
            if conversation.mode == ConversationMode.SALES_AI.value:
                ai = AIGateway.generate_sales_reply(
                    conversation_id=conversation.id, message_id=result.message.id
                )
            elif conversation.mode == ConversationMode.INTERNAL_ASSISTANT.value:
                ai = AIGateway.generate_assistant_reply(
                    conversation_id=conversation.id, message_id=result.message.id
                )
            else:
                ai = AIGateway.generate_support_reply(
                    conversation_id=conversation.id, message_id=result.message.id
                )
        except Exception as exc:  # noqa: BLE001 — never 500 the bridge
            return None, False, f"ai_error: {type(exc).__name__}"

        data = ai.data or {}
        candidate = (data.get("reply") or ai.text or "").strip()
        if not ai.can_send_reply or not candidate:
            return None, False, "blocked_or_empty"

        # Persist the outbound so it shows in the Inbox.
        MessageIngestionService.ingest(
            organization=org,
            channel=Channel.WHATSAPP,
            direction=MessageDirection.OUTBOUND,
            contact=result.contact,
            conversation=conversation,
            message_type=MessageType.TEXT,
            body=candidate,
            status=MessageStatus.SENT,
        )
        return candidate, True, "ai_reply"

    @staticmethod
    def _interpret_prospect_reply(*, org, conversation, result, request):
        from crm.prospecting.services.replies import ProspectReplyInterpreter

        try:
            interpreted = ProspectReplyInterpreter.interpret_inbound(
                organization=org,
                conversation=conversation,
                contact=result.contact,
                message=result.message,
                request=request,
            )
        except Exception as exc:  # noqa: BLE001 - bridge must not 500
            return {"reason": f"prospecting_error: {type(exc).__name__}"}
        if interpreted is None:
            return None
        return {
            "prospect_id": str(interpreted.prospect.id),
            "intent": interpreted.intent,
            "status": interpreted.prospect.status,
            "lead_id": interpreted.lead_id,
            "opted_out": interpreted.opted_out,
        }

    @staticmethod
    def _run_document_command(org, conversation, result, *, doc_type, fmt, body):
        """Owner command: AI-draft a document, generate the file, return its URL.

        Returns ``(reply_text, should_send, reason, document)`` where ``document``
        is a dict the Node bridge uses to send the file (or ``None`` on failure).
        Never raises — the bridge must not 500.
        """
        from crm.ai.services.ai_gateway import AIGateway
        from crm.documents.domain.enums import DOCUMENT_TYPE_LABELS
        from crm.documents.services.brand_kit import BrandKitService
        from crm.documents.services.document_service import DocumentService

        parts = body.split(None, 1)
        request_text = parts[1].strip() if len(parts) > 1 else ""

        try:
            kit = BrandKitService.get_or_create(org)
            refs = {"conversation_id": conversation.id, "contact_id": result.contact.id}
            ai = AIGateway.generate_document_draft(
                organization_id=org.id,
                owner_request=request_text or body,
                doc_type=doc_type,
                currency=kit.currency or "",
                tax_rate=kit.default_tax_rate,
                default_terms=kit.default_terms or "",
                references=refs,
            )
            if not ai.succeeded or not ai.data:
                return None, False, f"doc_draft_failed: {ai.error_code or 'unknown'}", None

            doc = DocumentService.generate(
                organization=org,
                doc_type=doc_type,
                fmt=fmt,
                payload=ai.data,
                references={**refs, "ai_run_id": ai.run_id},
            )
            signed = DocumentService.signed_url(doc)
        except Exception as exc:  # noqa: BLE001 — never 500 the bridge
            return None, False, f"doc_error: {type(exc).__name__}", None

        if signed is None:
            return None, False, "doc_no_file", None

        label = DOCUMENT_TYPE_LABELS.get(doc_type, "Documento")
        caption = f"📄 ¡Listo! Te preparé «{doc.title}» ({label}). Te lo paso adjunto 👇"
        DocumentService.mark_sent(doc)
        # Leave a trace in the Inbox so the conversation reflects the delivery.
        MessageIngestionService.ingest(
            organization=org,
            channel=Channel.WHATSAPP,
            direction=MessageDirection.OUTBOUND,
            contact=result.contact,
            conversation=conversation,
            message_type=MessageType.TEXT,
            body=caption,
            status=MessageStatus.SENT,
        )
        document = {
            "url": signed.url,
            "expires_in": signed.expires_in,
            "file_name": doc.media_asset.file_name,
            "mime_type": doc.media_asset.mime_type,
            "title": doc.title,
        }
        return caption, True, "document_generated", document


class WhatsAppBridgeOutboxView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        _require_secret(request)
        org = _resolve_org(request)
        try:
            limit = int(request.query_params.get("limit", "20"))
        except (TypeError, ValueError):
            limit = 20

        from crm.whatsapp.services.outbound_queue import WhatsAppOutboundQueueService

        rows = WhatsAppOutboundQueueService.claim_pending(organization=org, limit=limit)
        return success_response(
            request,
            [
                {
                    "id": str(row.id),
                    "phone": row.contact_phone,
                    "body": row.body,
                    "idempotency_key": row.idempotency_key,
                }
                for row in rows
            ],
        )


class WhatsAppBridgeDeliveryStatusView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        _require_secret(request)
        org = _resolve_org(request)
        message_id = str(request.data.get("message_id") or "").strip()
        status = str(request.data.get("status") or "").strip()
        reason = str(request.data.get("reason") or "").strip()
        if not message_id:
            raise ValidationError({"message_id": "requerido"})

        from crm.whatsapp.services.outbound_queue import WhatsAppOutboundQueueService

        outbound = WhatsAppOutboundQueueService.record_delivery_status(
            organization=org,
            message_id=message_id,
            status=status,
            reason=reason,
        )
        return success_response(
            request,
            {
                "id": str(outbound.id),
                "status": outbound.status,
                "attempts": outbound.attempts,
                "available_at": outbound.available_at.isoformat(),
                "sent_at": outbound.sent_at.isoformat() if outbound.sent_at else None,
            },
        )


class WhatsAppBridgeStatusView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.SETTINGS_MANAGE.value

    def get(self, request):
        organization = resolve_current_organization(request)
        cached = cache.get(_cache_key(organization.id))
        if not cached:
            return success_response(
                request, {"state": "disconnected", "qr": None, "info": {}, "updated_at": None}
            )
        return success_response(request, cached)
