"""SupportTicketCreator: the single path that creates tickets.

Supports text messages, manual creation and validated AI extractions. Always:
client/contact resolved, triage applied (rules + AI, backend owns the result),
deduplicated by ``source_message_id``, ``created`` event recorded, urgent/critical
tickets notify the owner. Never parses free text to mutate data — AI tickets must
come from a validated structured extraction passed in by the caller.
"""

from dataclasses import dataclass

from django.db import IntegrityError, transaction

from crm.audit.services import audit_event_create
from crm.clients.services.client_resolver import ClientResolver
from crm.core.services.outbox import create_outbox_event
from crm.support.domain import events
from crm.support.domain.enums import ActorType, TicketEventType, TicketStatus
from crm.support.domain.exceptions import DuplicateTicketError
from crm.support.models import SupportTicket

from ._support import org_stub, record_event
from .known_issue_matcher import KnownIssueMatcher
from .ticket_triage import SupportTriageService
from .urgent_ticket_notifier import SupportUrgentTicketNotifier


@dataclass(frozen=True)
class TicketCreationResult:
    ticket: SupportTicket
    created: bool
    suggested_reply: str = ""
    known_issue_id: str | None = None


class SupportTicketCreator:
    @staticmethod
    def _existing_for_source(organization_id, source_message_id) -> SupportTicket | None:
        if source_message_id is None:
            return None
        return SupportTicket.objects.filter(
            organization_id=organization_id, source_message_id=source_message_id
        ).first()

    @staticmethod
    def _resolve_client(organization_id, contact_id):
        resolution = ClientResolver.resolve_by_contact(contact_id, organization_id)
        return resolution.client_id, resolution.support_level

    @staticmethod
    @transaction.atomic
    def _create(
        *,
        organization,
        contact,
        title: str,
        description: str,
        triage,
        conversation_id=None,
        source_message_id=None,
        technical_summary: str = "",
        ai_summary: str = "",
        actor=None,
        actor_type: str = ActorType.USER.value,
        request=None,
        suggested_reply: str = "",
    ) -> TicketCreationResult:
        existing = SupportTicketCreator._existing_for_source(organization.id, source_message_id)
        if existing is not None:
            return TicketCreationResult(
                ticket=existing, created=False, suggested_reply=suggested_reply
            )

        client_id, _support_level = SupportTicketCreator._resolve_client(
            organization.id, contact.id
        )
        status = triage.suggested_status or TicketStatus.TRIAGED.value

        try:
            ticket = SupportTicket.objects.create(
                organization_id=organization.id,
                client_id=client_id,
                contact=contact,
                conversation_id=conversation_id,
                source_message_id=source_message_id,
                status=status,
                priority=triage.priority,
                category=triage.category,
                title=title[:255],
                description=description,
                technical_summary=technical_summary,
                ai_summary=ai_summary,
                created_by_id=getattr(actor, "id", None),
            )
        except IntegrityError as exc:
            existing = SupportTicketCreator._existing_for_source(organization.id, source_message_id)
            if existing is not None:
                return TicketCreationResult(ticket=existing, created=False)
            raise DuplicateTicketError() from exc

        record_event(
            ticket,
            event_type=TicketEventType.CREATED,
            actor_type=actor_type,
            actor_id=getattr(actor, "id", None),
            to_status=status,
            payload={"priority": triage.priority, "category": triage.category},
        )
        record_event(
            ticket,
            event_type=TicketEventType.TRIAGED,
            actor_type=ActorType.SYSTEM.value,
            payload=triage.as_dict(),
        )

        # Suggest (never auto-apply) a related known issue.
        known = KnownIssueMatcher.match(
            organization_id=organization.id,
            text=f"{title}\n{description}",
            category=triage.category,
        )
        if known is not None:
            ticket.metadata = {**(ticket.metadata or {}), "known_issue_id": known.known_issue_id}
            ticket.save(update_fields=["metadata", "updated_at"])

        create_outbox_event(
            event_type=events.TICKET_CREATED,
            organization_id=organization.id,
            payload={
                "event_type": events.TICKET_CREATED,
                "organization_id": str(organization.id),
                "data": {
                    "ticket_id": str(ticket.id),
                    "contact_id": str(contact.id),
                    "priority": triage.priority,
                    "category": triage.category,
                    "conversation_id": str(conversation_id) if conversation_id else None,
                },
                "metadata": {"request_id": getattr(request, "request_id", None)},
            },
        )
        if actor is not None:
            audit_event_create(
                event_type="support_ticket_created",
                actor=actor,
                organization=org_stub(organization.id),
                request=request,
                resource_type="support_ticket",
                resource_id=str(ticket.id),
                metadata={"priority": triage.priority, "category": triage.category},
            )

        if triage.requires_owner_notification:
            create_outbox_event(
                event_type=events.TICKET_URGENT_DETECTED,
                organization_id=organization.id,
                payload={
                    "event_type": events.TICKET_URGENT_DETECTED,
                    "organization_id": str(organization.id),
                    "data": {"ticket_id": str(ticket.id), "priority": triage.priority},
                    "metadata": {},
                },
            )
            SupportUrgentTicketNotifier.notify(
                ticket=ticket, reason="; ".join(triage.reasons)[:300], actor=actor, request=request
            )

        return TicketCreationResult(
            ticket=ticket,
            created=True,
            suggested_reply=suggested_reply,
            known_issue_id=known.known_issue_id if known else None,
        )

    # -- public entrypoints --------------------------------------------------

    @staticmethod
    def create_from_message(
        *, conversation_id, message_id, actor=None, request=None
    ) -> TicketCreationResult:
        from crm.conversations.models import Message

        message = Message.objects.select_related("conversation", "contact").get(
            id=message_id, conversation_id=conversation_id
        )
        organization = _organization(message.organization_id)
        _client_id, support_level = SupportTicketCreator._resolve_client(
            organization.id, message.contact_id
        )
        text = message.body or message.normalized_text or ""
        triage = SupportTriageService.triage(
            text=text, organization_id=organization.id, support_level=support_level
        )
        title = (text[:80] or "Solicitud de soporte").strip()
        return SupportTicketCreator._create(
            organization=organization,
            contact=message.contact,
            title=title,
            description=text,
            triage=triage,
            conversation_id=message.conversation_id,
            source_message_id=message.id,
            actor=actor,
            actor_type=ActorType.USER.value if actor else ActorType.SYSTEM.value,
            request=request,
        )

    @staticmethod
    def create_manual(*, organization, contact, payload: dict, created_by=None, request=None):
        triage = SupportTriageService.triage(
            text=f"{payload.get('title', '')} {payload.get('description', '')}",
            organization_id=organization.id,
            ai_category=payload.get("category"),
            ai_priority=payload.get("priority"),
        )
        return SupportTicketCreator._create(
            organization=organization,
            contact=contact,
            title=payload["title"],
            description=payload.get("description", ""),
            triage=triage,
            conversation_id=payload.get("conversation_id"),
            actor=created_by,
            request=request,
        )

    @staticmethod
    def create_from_ai_extraction(
        *,
        organization,
        contact,
        extraction: dict,
        conversation_id=None,
        source_message_id=None,
        actor=None,
        request=None,
    ) -> TicketCreationResult:
        """``extraction`` MUST be a schema-validated SupportTicket dict."""
        support_level = SupportTicketCreator._resolve_client(organization.id, contact.id)[1]
        triage = SupportTriageService.triage(
            text=f"{extraction.get('title', '')} {extraction.get('description', '')}",
            organization_id=organization.id,
            support_level=support_level,
            ai_category=extraction.get("category"),
            ai_priority=extraction.get("priority"),
            missing_information=extraction.get("missing_information"),
        )
        return SupportTicketCreator._create(
            organization=organization,
            contact=contact,
            title=extraction["title"],
            description=extraction.get("description", ""),
            triage=triage,
            conversation_id=conversation_id,
            source_message_id=source_message_id,
            ai_summary=extraction.get("owner_summary", ""),
            technical_summary=extraction.get("description", "")[:2000],
            actor=actor,
            actor_type=ActorType.AI_AGENT.value,
            request=request,
            suggested_reply=extraction.get("suggested_reply", ""),
        )


def _organization(organization_id):
    from crm.organizations.models import Organization

    return Organization.objects.get(id=organization_id)
