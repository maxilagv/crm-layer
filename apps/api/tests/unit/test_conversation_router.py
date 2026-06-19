"""Pure unit tests for ConversationRouter (no DB)."""

from types import SimpleNamespace

from crm.contacts.constants import ContactStatus, ContactType
from crm.conversations.constants import ConversationMode, ConversationStatus
from crm.conversations.router import route


def _contact(type=ContactType.LEAD, status=ContactStatus.ACTIVE):
    return SimpleNamespace(type=type.value, status=status.value)


def _conversation(mode=ConversationMode.SALES_AI, status=ConversationStatus.OPEN, ai_enabled=True):
    return SimpleNamespace(mode=mode.value, status=status.value, ai_enabled=ai_enabled)


def test_router_for_lead():
    assert route(_contact(ContactType.LEAD)) == ConversationMode.SALES_AI.value


def test_router_for_client():
    assert route(_contact(ContactType.CLIENT)) == ConversationMode.SUPPORT_AI.value


def test_router_for_internal():
    assert route(_contact(ContactType.INTERNAL)) == ConversationMode.INTERNAL_ASSISTANT.value


def test_router_unknown_falls_back_to_manual():
    assert route(_contact(ContactType.UNKNOWN)) == ConversationMode.MANUAL.value


def test_router_supplier_falls_back_to_manual():
    assert route(_contact(ContactType.SUPPLIER)) == ConversationMode.MANUAL.value


def test_router_blocked_status_returns_blocked():
    contact = _contact(ContactType.LEAD, status=ContactStatus.BLOCKED)
    assert route(contact) == ConversationMode.BLOCKED.value


def test_router_blocked_type_returns_blocked():
    assert route(_contact(ContactType.BLOCKED)) == ConversationMode.BLOCKED.value


def test_router_paused_conversation_returns_paused():
    contact = _contact(ContactType.LEAD)
    conversation = _conversation(mode=ConversationMode.PAUSED)
    assert route(contact, conversation) == ConversationMode.PAUSED.value


def test_router_ai_disabled_returns_manual():
    contact = _contact(ContactType.CLIENT)
    conversation = _conversation(mode=ConversationMode.SUPPORT_AI, ai_enabled=False)
    assert route(contact, conversation) == ConversationMode.MANUAL.value


def test_router_closed_conversation_keeps_mode():
    contact = _contact(ContactType.LEAD)
    conversation = _conversation(mode=ConversationMode.MANUAL, status=ConversationStatus.CLOSED)
    assert route(contact, conversation) == ConversationMode.MANUAL.value


def test_router_blocked_beats_everything():
    contact = _contact(ContactType.BLOCKED, status=ContactStatus.ACTIVE)
    conversation = _conversation(mode=ConversationMode.PAUSED)
    assert route(contact, conversation) == ConversationMode.BLOCKED.value
