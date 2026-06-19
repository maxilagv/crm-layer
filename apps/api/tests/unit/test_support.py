import pytest

from crm.core.models import OutboxEvent
from crm.support.domain.enums import (
    CommentVisibility,
    ResolvedByType,
    TicketCategory,
    TicketEventType,
    TicketPriority,
    TicketStatus,
)
from crm.support.domain.exceptions import CriticalTicketAIResolveDenied
from crm.support.models import SupportTicket, SupportTicketEvent
from crm.support.services.known_issue_matcher import KnownIssueMatcher
from crm.support.services.ticket_creator import SupportTicketCreator
from crm.support.services.ticket_lifecycle import TicketLifecycleService
from crm.support.services.ticket_triage import SupportTriageService
from tests.factories.accounts import UserFactory
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory, MessageFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory
from tests.factories.support import SupportKnownIssueFactory, SupportTicketFactory

# --------------------------------------------------------------- triage rules


@pytest.mark.parametrize(
    "text,expected_category",
    [
        ("No puedo acceder, me pide la contraseña", TicketCategory.ACCESS.value),
        ("Tengo un problema con el pago de la factura", TicketCategory.BILLING.value),
        ("La integración con WhatsApp por la API falla", TicketCategory.INTEGRATION.value),
        ("El sistema está muy lento, tarda mucho", TicketCategory.PERFORMANCE.value),
    ],
)
def test_triage_category_rules(text, expected_category):
    result = SupportTriageService.triage(text=text)
    assert result.category == expected_category


def test_triage_production_down_is_urgent_or_critical():
    result = SupportTriageService.triage(text="Producción caída, los clientes no pueden operar")
    assert result.priority in (TicketPriority.URGENT.value, TicketPriority.CRITICAL.value)
    assert result.requires_owner_notification is True


def test_triage_vip_elevates_priority():
    base = SupportTriageService.triage(text="Tengo una consulta")
    vip = SupportTriageService.triage(text="Tengo una consulta", support_level="vip")
    assert base.priority == TicketPriority.MEDIUM.value
    assert vip.priority == TicketPriority.HIGH.value


def test_triage_ai_can_raise_but_not_lower_priority():
    result = SupportTriageService.triage(
        text="Consulta simple", ai_priority=TicketPriority.URGENT.value
    )
    assert result.priority == TicketPriority.URGENT.value
    lowered = SupportTriageService.triage(
        text="Producción caída", ai_priority=TicketPriority.LOW.value
    )
    assert lowered.priority in (TicketPriority.URGENT.value, TicketPriority.CRITICAL.value)


def test_triage_missing_information_sets_waiting_client():
    result = SupportTriageService.triage(text="No anda", missing_information=["captura"])
    assert result.suggested_status == TicketStatus.WAITING_CLIENT.value


# ------------------------------------------------------------ ticket creation


@pytest.mark.django_db
def test_ticket_created_from_text_message():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id)
    conversation = ConversationFactory(organization_id=org.id, contact=contact)
    message = MessageFactory(conversation=conversation, body="No puedo acceder, error de login")
    result = SupportTicketCreator.create_from_message(
        conversation_id=conversation.id, message_id=message.id
    )
    assert result.created is True
    assert result.ticket.category == TicketCategory.ACCESS.value
    assert result.ticket.source_message_id == message.id
    assert SupportTicketEvent.objects.filter(
        ticket=result.ticket, event_type=TicketEventType.CREATED
    ).exists()
    assert OutboxEvent.objects.filter(event_type="support.ticket_created.v1").exists()


@pytest.mark.django_db
def test_ticket_duplicate_source_message_prevented():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id)
    conversation = ConversationFactory(organization_id=org.id, contact=contact)
    message = MessageFactory(conversation=conversation, body="Algo falla")
    first = SupportTicketCreator.create_from_message(
        conversation_id=conversation.id, message_id=message.id
    )
    second = SupportTicketCreator.create_from_message(
        conversation_id=conversation.id, message_id=message.id
    )
    assert first.created is True
    assert second.created is False
    assert SupportTicket.objects.filter(source_message_id=message.id).count() == 1


@pytest.mark.django_db
def test_urgent_ticket_notifies_owner_once():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id)
    conversation = ConversationFactory(organization_id=org.id, contact=contact)
    message = MessageFactory(conversation=conversation, body="Producción caída, no podemos operar")
    result = SupportTicketCreator.create_from_message(
        conversation_id=conversation.id, message_id=message.id
    )
    assert result.ticket.priority in (TicketPriority.URGENT.value, TicketPriority.CRITICAL.value)
    notified_events = SupportTicketEvent.objects.filter(
        ticket=result.ticket, event_type=TicketEventType.OWNER_NOTIFIED
    )
    assert notified_events.count() == 1
    assert OutboxEvent.objects.filter(event_type="support.owner_notified.v1").count() == 1

    # Re-notifying the same ticket is a no-op (idempotent).
    from crm.support.services.urgent_ticket_notifier import SupportUrgentTicketNotifier

    assert SupportUrgentTicketNotifier.notify(ticket=result.ticket, reason="again") is False
    assert notified_events.count() == 1


@pytest.mark.django_db
def test_non_urgent_ticket_does_not_notify():
    org = OrganizationFactory()
    contact = ContactFactory(organization_id=org.id)
    conversation = ConversationFactory(organization_id=org.id, contact=contact)
    message = MessageFactory(conversation=conversation, body="Una consulta tranquila")
    result = SupportTicketCreator.create_from_message(
        conversation_id=conversation.id, message_id=message.id
    )
    assert not SupportTicketEvent.objects.filter(
        ticket=result.ticket, event_type=TicketEventType.OWNER_NOTIFIED
    ).exists()


# ----------------------------------------------------------------- lifecycle


@pytest.mark.django_db
def test_ticket_status_lifecycle():
    org = OrganizationFactory()
    user = UserFactory()
    MembershipFactory(organization=org, user=user)
    ticket = SupportTicketFactory(organization_id=org.id)

    TicketLifecycleService.assign(ticket=ticket, user=user, actor=user)
    ticket.refresh_from_db()
    assert ticket.assigned_user_id == user.id
    assert ticket.status == TicketStatus.IN_PROGRESS.value

    TicketLifecycleService.resolve(ticket=ticket, resolution={"summary": "Resuelto"}, actor=user)
    ticket.refresh_from_db()
    assert ticket.status == TicketStatus.RESOLVED.value
    assert ticket.resolved_at is not None
    assert ticket.resolutions.count() == 1

    TicketLifecycleService.reopen(ticket=ticket, reason="vuelve a fallar", actor=user)
    ticket.refresh_from_db()
    assert ticket.status == TicketStatus.IN_PROGRESS.value
    assert ticket.resolved_at is None

    for event_type in (
        TicketEventType.ASSIGNED,
        TicketEventType.RESOLVED,
        TicketEventType.REOPENED,
    ):
        assert SupportTicketEvent.objects.filter(ticket=ticket, event_type=event_type).exists()


@pytest.mark.django_db
def test_critical_ticket_cannot_be_resolved_by_ai_only():
    org = OrganizationFactory()
    ticket = SupportTicketFactory(organization_id=org.id, priority=TicketPriority.CRITICAL)
    with pytest.raises(CriticalTicketAIResolveDenied):
        TicketLifecycleService.resolve(
            ticket=ticket,
            resolution={"summary": "x"},
            resolved_by_type=ResolvedByType.AI_AGENT.value,
        )
    # A human may still resolve it.
    TicketLifecycleService.resolve(ticket=ticket, resolution={"summary": "ok"})
    ticket.refresh_from_db()
    assert ticket.status == TicketStatus.RESOLVED.value


@pytest.mark.django_db
def test_ticket_comment_internal_records_event():
    org = OrganizationFactory()
    user = UserFactory()
    ticket = SupportTicketFactory(organization_id=org.id)
    comment = TicketLifecycleService.add_comment(
        ticket=ticket, body="nota interna", visibility=CommentVisibility.INTERNAL.value, actor=user
    )
    assert comment.visibility == CommentVisibility.INTERNAL.value
    assert SupportTicketEvent.objects.filter(
        ticket=ticket, event_type=TicketEventType.COMMENT_ADDED
    ).exists()


# --------------------------------------------------------------- known issues


@pytest.mark.django_db
def test_known_issue_matcher_suggests_related():
    org = OrganizationFactory()
    SupportKnownIssueFactory(organization_id=org.id, matching_keywords=["whatsapp", "integracion"])
    match = KnownIssueMatcher.match(
        organization_id=org.id, text="Falla la integración de WhatsApp", category=None
    )
    assert match is not None
    assert match.score >= 1
