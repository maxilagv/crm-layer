"""Write-side operations for conversations and messages.

All mutations run in ``transaction.atomic`` and persist their internal events
through the outbox in the same transaction, so a Redis/Celery outage after a
commit never loses the event. No external provider (WhatsApp) or AI is called
here; outbound sends are simulated by persisting a message + event.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from crm.audit.services import audit_event_create
from crm.contacts.constants import ContactSource, ContactType
from crm.contacts.services import ContactResolver
from crm.core.services.outbox import create_outbox_event

from .constants import (
    ACTIVE_STATUSES,
    EVENT_CONVERSATION_CREATED,
    EVENT_HANDOFF_REQUESTED,
    EVENT_MESSAGE_RECEIVED,
    EVENT_MESSAGE_SENT,
    EVENT_MODE_CHANGED,
    IMPORTANCE_MAX,
    IMPORTANCE_MIN,
    Channel,
    ConversationMode,
    ConversationStatus,
    MemoryType,
    MessageDirection,
    MessageStatus,
    MessageType,
    SummaryType,
)
from .models import (
    Conversation,
    ConversationMemory,
    ConversationSummary,
    Message,
    MessageAttachment,
)
from .normalizers import clean_body, normalize_text
from .router import route

logger = logging.getLogger(__name__)
MEMORY_EXTRACTION_INBOUND_INTERVAL = 6


def _actor_id(actor):
    return getattr(actor, "id", None)


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()


def _emit_event(event_type: str, *, organization_id, data: dict, request=None) -> None:
    create_outbox_event(
        event_type=event_type,
        organization_id=organization_id,
        payload={
            "event_type": event_type,
            "organization_id": str(organization_id),
            "data": data,
            "metadata": {"request_id": getattr(request, "request_id", None)},
        },
    )


# --- conversation resolution ----------------------------------------------


@dataclass(frozen=True)
class ConversationResolveResult:
    conversation: Conversation | None
    created: bool


class ConversationResolver:
    """Reuse an open/pending conversation for (contact, channel) or create one."""

    @staticmethod
    @transaction.atomic
    def resolve(
        *,
        organization,
        contact,
        channel: str,
        create: bool = True,
        assigned_user=None,
        request=None,
    ) -> ConversationResolveResult:
        existing = (
            Conversation.objects.filter(
                organization_id=organization.id,
                contact=contact,
                channel=channel,
                status__in=[status.value for status in ACTIVE_STATUSES],
            )
            .order_by(F("last_message_at").desc(nulls_last=True), "-created_at")
            .first()
        )
        if existing is not None:
            return ConversationResolveResult(conversation=existing, created=False)
        if not create:
            return ConversationResolveResult(conversation=None, created=False)

        conversation = Conversation.objects.create(
            organization_id=organization.id,
            contact=contact,
            channel=channel,
            status=ConversationStatus.OPEN,
            mode=route(contact, None),
            assigned_user=assigned_user,
        )
        _emit_event(
            EVENT_CONVERSATION_CREATED,
            organization_id=organization.id,
            data={
                "conversation_id": str(conversation.id),
                "contact_id": str(contact.id),
                "channel": channel,
            },
            request=request,
        )
        return ConversationResolveResult(conversation=conversation, created=True)


# --- message ingestion -----------------------------------------------------


@dataclass(frozen=True)
class IngestionResult:
    contact: object
    conversation: Conversation
    message: Message
    created_contact: bool
    created_conversation: bool
    deduplicated: bool


def _touch_conversation_timestamps(conversation: Conversation, direction: str, when) -> None:
    fields = ["last_message_at", "updated_at"]
    conversation.last_message_at = when
    if direction == MessageDirection.INBOUND:
        conversation.last_inbound_at = when
        fields.append("last_inbound_at")
    elif direction == MessageDirection.OUTBOUND:
        conversation.last_outbound_at = when
        fields.append("last_outbound_at")
    conversation.save(update_fields=fields)


class MessageNormalizer:
    """Namespaced access to body/text normalization."""

    clean_body = staticmethod(clean_body)
    normalize_text = staticmethod(normalize_text)


class MessageIngestionService:
    """Persist an inbound/outbound message, resolving contact + conversation.

    Deduplicates by ``external_message_id`` within the organization. Never calls
    a real provider; ``raw_payload`` is stored verbatim for audit but never
    exposed by the public API.
    """

    @staticmethod
    @transaction.atomic
    def ingest(
        *,
        organization,
        channel: str,
        direction: str,
        contact=None,
        phone: str | None = None,
        region: str | None = None,
        conversation: Conversation | None = None,
        message_type: str = MessageType.TEXT,
        body: str = "",
        external_message_id: str = "",
        external_timestamp=None,
        status: str | None = None,
        raw_payload: dict | None = None,
        attachments: list[dict] | None = None,
        actor=None,
        request=None,
    ) -> IngestionResult:
        created_contact = False
        if contact is None:
            if not phone:
                raise ValueError("ingest requires either a contact or a phone number")
            source = ContactSource.WHATSAPP if channel == Channel.WHATSAPP else ContactSource.SYSTEM
            resolved = ContactResolver.resolve_by_phone(
                organization=organization,
                raw_phone=phone,
                region=region,
                create=True,
                contact_type=ContactType.LEAD
                if direction == MessageDirection.INBOUND
                else ContactType.UNKNOWN,
                source=source,
                request=request,
            )
            contact = resolved.contact
            created_contact = resolved.created

        # Deduplicate by external id before creating anything.
        if external_message_id:
            existing = (
                Message.objects.filter(
                    organization_id=organization.id, external_message_id=external_message_id
                )
                .select_related("conversation", "contact")
                .first()
            )
            if existing is not None:
                return IngestionResult(
                    contact=existing.contact,
                    conversation=existing.conversation,
                    message=existing,
                    created_contact=created_contact,
                    created_conversation=False,
                    deduplicated=True,
                )

        created_conversation = False
        if conversation is None:
            conv_result = ConversationResolver.resolve(
                organization=organization, contact=contact, channel=channel, request=request
            )
            conversation = conv_result.conversation
            created_conversation = conv_result.created

        default_status = (
            MessageStatus.RECEIVED
            if direction == MessageDirection.INBOUND
            else MessageStatus.QUEUED
        )
        try:
            message = Message.objects.create(
                organization_id=organization.id,
                conversation=conversation,
                contact=contact,
                direction=direction,
                message_type=message_type,
                body=clean_body(body),
                normalized_text=normalize_text(body),
                external_message_id=external_message_id,
                external_timestamp=external_timestamp,
                status=status or default_status,
                raw_payload=raw_payload or {},
                created_by_id=_actor_id(actor),
            )
        except IntegrityError:
            # Concurrent ingest of the same external id; recover the winner.
            existing = (
                Message.objects.filter(
                    organization_id=organization.id, external_message_id=external_message_id
                )
                .select_related("conversation", "contact")
                .first()
            )
            return IngestionResult(
                contact=contact,
                conversation=existing.conversation if existing else conversation,
                message=existing,
                created_contact=created_contact,
                created_conversation=created_conversation,
                deduplicated=True,
            )

        for attachment in attachments or []:
            MessageAttachment.objects.create(
                organization_id=organization.id,
                message=message,
                external_media_id=attachment.get("external_media_id", ""),
                mime_type=attachment.get("mime_type", ""),
                file_name=attachment.get("file_name", ""),
                size_bytes=attachment.get("size_bytes"),
                metadata=attachment.get("metadata", {}),
            )

        _touch_conversation_timestamps(conversation, direction, message.created_at)

        if direction == MessageDirection.INBOUND:
            _emit_event(
                EVENT_MESSAGE_RECEIVED,
                organization_id=organization.id,
                data={
                    "conversation_id": str(conversation.id),
                    "contact_id": str(contact.id),
                    "message_id": str(message.id),
                    "channel": channel,
                    "direction": direction,
                },
                request=request,
            )
            _schedule_memory_extraction_if_due(conversation)
        elif direction == MessageDirection.OUTBOUND:
            _emit_event(
                EVENT_MESSAGE_SENT,
                organization_id=organization.id,
                data={
                    "conversation_id": str(conversation.id),
                    "contact_id": str(contact.id),
                    "message_id": str(message.id),
                    "channel": channel,
                    "direction": direction,
                },
                request=request,
            )

        return IngestionResult(
            contact=contact,
            conversation=conversation,
            message=message,
            created_contact=created_contact,
            created_conversation=created_conversation,
            deduplicated=False,
        )


def _schedule_memory_extraction_if_due(conversation: Conversation) -> None:
    inbound_count = Message.objects.filter(
        organization_id=conversation.organization_id,
        conversation=conversation,
        direction=MessageDirection.INBOUND,
        deleted_at__isnull=True,
    ).count()
    if (
        inbound_count < MEMORY_EXTRACTION_INBOUND_INTERVAL
        or inbound_count % MEMORY_EXTRACTION_INBOUND_INTERVAL != 0
    ):
        return
    if not _memory_extraction_is_configured(conversation.organization_id):
        return
    conversation_id = str(conversation.id)
    transaction.on_commit(lambda: _dispatch_memory_extraction(conversation_id))


def _memory_extraction_is_configured(organization_id) -> bool:
    from crm.ai.domain.enums import AIPurpose
    from crm.ai.models import AIModelConfig, AIPrompt

    purpose = AIPurpose.MEMORY_EXTRACTION.value
    return (
        AIModelConfig.objects.filter(
            organization_id=organization_id,
            purpose=purpose,
            is_active=True,
        ).exists()
        and AIPrompt.objects.filter(
            organization_id=organization_id,
            purpose=purpose,
            active_version__isnull=False,
        ).exists()
    )


def _dispatch_memory_extraction(conversation_id: str) -> None:
    try:
        from crm.ai.tasks import extract_conversation_memory

        extract_conversation_memory.delay(conversation_id=conversation_id)
    except Exception as exc:  # noqa: BLE001 - memory extraction must never block inbound ingest
        logger.warning(
            "Conversation memory extraction dispatch failed",
            extra={
                "event": "conversation.memory_dispatch_failed",
                "metadata": {
                    "conversation_id": conversation_id,
                    "error": type(exc).__name__,
                },
            },
        )


# --- handoff / mode changes ------------------------------------------------


def _emit_mode_change(conversation, previous_mode, *, event_type, request) -> None:
    _emit_event(
        event_type,
        organization_id=conversation.organization_id,
        data={
            "conversation_id": str(conversation.id),
            "contact_id": str(conversation.contact_id),
            "previous_mode": previous_mode,
            "mode": conversation.mode,
            "ai_enabled": conversation.ai_enabled,
            "status": conversation.status,
        },
        request=request,
    )


def _audit_conversation(conversation, *, actor, request, action: str, changes=None) -> None:
    if actor is None:
        return
    audit_event_create(
        event_type=action,
        actor=actor,
        organization=_org_stub(conversation.organization_id),
        request=request,
        resource_type="conversations_conversation",
        resource_id=str(conversation.id),
        changes=changes or {},
    )


class ConversationHandoffService:
    """Human control over a conversation's mode/status (takeover, pause, etc.)."""

    @staticmethod
    @transaction.atomic
    def takeover(*, conversation, actor, assigned_user=None, request=None) -> Conversation:
        previous_mode = conversation.mode
        conversation.mode = ConversationMode.MANUAL
        conversation.ai_enabled = False
        conversation.assigned_user = assigned_user or actor
        conversation.save(update_fields=["mode", "ai_enabled", "assigned_user", "updated_at"])
        _audit_conversation(
            conversation, actor=actor, request=request, action="conversation_takeover"
        )
        _emit_mode_change(
            conversation, previous_mode, event_type=EVENT_HANDOFF_REQUESTED, request=request
        )
        return conversation

    @staticmethod
    @transaction.atomic
    def pause_ai(*, conversation, actor, request=None) -> Conversation:
        previous_mode = conversation.mode
        conversation.ai_enabled = False
        conversation.mode = ConversationMode.PAUSED
        conversation.save(update_fields=["ai_enabled", "mode", "updated_at"])
        _audit_conversation(
            conversation, actor=actor, request=request, action="conversation_paused"
        )
        _emit_mode_change(
            conversation, previous_mode, event_type=EVENT_MODE_CHANGED, request=request
        )
        return conversation

    @staticmethod
    @transaction.atomic
    def resume_ai(*, conversation, actor, request=None) -> Conversation:
        previous_mode = conversation.mode
        conversation.ai_enabled = True
        # Lift the pause before routing so the recomputed mode reflects the
        # contact type rather than the stale paused state.
        if conversation.mode == ConversationMode.PAUSED:
            conversation.mode = ConversationMode.MANUAL
        conversation.mode = route(conversation.contact, conversation)
        conversation.save(update_fields=["ai_enabled", "mode", "updated_at"])
        _audit_conversation(
            conversation, actor=actor, request=request, action="conversation_resumed"
        )
        _emit_mode_change(
            conversation, previous_mode, event_type=EVENT_MODE_CHANGED, request=request
        )
        return conversation

    @staticmethod
    @transaction.atomic
    def close(*, conversation, actor, request=None) -> Conversation:
        conversation.status = ConversationStatus.CLOSED
        conversation.save(update_fields=["status", "updated_at"])
        _audit_conversation(
            conversation, actor=actor, request=request, action="conversation_closed"
        )
        return conversation

    @staticmethod
    @transaction.atomic
    def reopen(*, conversation, actor, request=None) -> Conversation:
        previous_mode = conversation.mode
        conversation.status = ConversationStatus.OPEN
        conversation.mode = route(conversation.contact, conversation)
        conversation.save(update_fields=["status", "mode", "updated_at"])
        _audit_conversation(
            conversation, actor=actor, request=request, action="conversation_reopened"
        )
        _emit_mode_change(
            conversation, previous_mode, event_type=EVENT_MODE_CHANGED, request=request
        )
        return conversation


# --- summaries / memory (manual/simulated; no real AI) ---------------------


class ConversationSummaryService:
    @staticmethod
    def create(
        *,
        conversation,
        summary: str,
        summary_type: str = SummaryType.SHORT,
        source_message_from_id=None,
        source_message_to_id=None,
        created_by_ai_run_id=None,
    ) -> ConversationSummary:
        return ConversationSummary.objects.create(
            organization_id=conversation.organization_id,
            conversation=conversation,
            summary=summary,
            summary_type=summary_type,
            source_message_from_id=source_message_from_id,
            source_message_to_id=source_message_to_id,
            created_by_ai_run_id=created_by_ai_run_id,
        )


class ConversationMemoryService:
    @staticmethod
    def create(
        *,
        conversation,
        memory_type: str,
        content: str,
        importance: int = IMPORTANCE_MIN,
        expires_at=None,
        source_message_id=None,
        embedding_id=None,
    ) -> ConversationMemory:
        if not IMPORTANCE_MIN <= importance <= IMPORTANCE_MAX:
            raise ValueError(f"importance must be between {IMPORTANCE_MIN} and {IMPORTANCE_MAX}")
        return ConversationMemory.objects.create(
            organization_id=conversation.organization_id,
            conversation=conversation,
            contact=conversation.contact,
            memory_type=memory_type,
            content=content,
            importance=importance,
            expires_at=expires_at,
            source_message_id=source_message_id,
            embedding_id=embedding_id,
        )

    @staticmethod
    def active_memories(conversation):
        now = timezone.now()
        return (
            conversation.memories.filter(deleted_at__isnull=True)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
            .order_by("-importance", "-created_at")
        )

    @staticmethod
    def memories_for_contact(*, organization_id, contact_id, limit: int = 6):
        """Top non-expired long-term memories for a contact, across all its conversations."""
        now = timezone.now()
        return list(
            ConversationMemory.objects.filter(
                organization_id=organization_id,
                contact_id=contact_id,
                deleted_at__isnull=True,
            )
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
            .order_by("-importance", "-created_at")[:limit]
        )

    @staticmethod
    def persist_extracted_facts(*, conversation, facts: list[dict]) -> list[ConversationMemory]:
        """Persist AI-extracted memory facts: validate type, clamp importance, skip dupes."""
        valid_types = set(MemoryType.values)
        existing = set(
            ConversationMemory.objects.filter(
                organization_id=conversation.organization_id,
                contact_id=conversation.contact_id,
                deleted_at__isnull=True,
            ).values_list("content", flat=True)
        )
        now = timezone.now()
        created: list[ConversationMemory] = []
        for fact in facts or []:
            content = (fact.get("content") or "").strip()
            memory_type = fact.get("memory_type")
            if not content or memory_type not in valid_types or content in existing:
                continue
            try:
                importance = int(fact.get("importance", IMPORTANCE_MIN))
            except (TypeError, ValueError):
                importance = IMPORTANCE_MIN
            importance = max(IMPORTANCE_MIN, min(IMPORTANCE_MAX, importance))
            expires_at = None
            days = fact.get("expires_in_days")
            if days:
                try:
                    expires_at = now + timedelta(days=int(days))
                except (TypeError, ValueError):
                    expires_at = None
            created.append(
                ConversationMemoryService.create(
                    conversation=conversation,
                    memory_type=memory_type,
                    content=content[:2000],
                    importance=importance,
                    expires_at=expires_at,
                )
            )
            existing.add(content)
        return created
