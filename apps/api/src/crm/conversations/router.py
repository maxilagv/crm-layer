"""ConversationRouter: pure, testable decision of a conversation's operative mode.

Rules are applied in a fixed order — hard restrictions first, then contact-type
classification, then a safe fallback. The function never mutates anything; the
handoff/ingestion services call it and persist the result. ``conversation`` is
optional so the resolver can compute an initial mode before a row exists.

Note on resume-ai: a paused conversation stays paused here by design. The
handoff service lifts the pause (clears the paused mode and sets ai_enabled=True)
*before* calling ``route`` so the recomputed mode reflects the contact type.
"""

from crm.contacts.constants import ContactStatus, ContactType

from .constants import ConversationMode, ConversationStatus


def route(contact, conversation=None) -> str:
    # 1. Hard restriction: blocked contact.
    if contact.status == ContactStatus.BLOCKED or contact.type == ContactType.BLOCKED:
        return ConversationMode.BLOCKED.value

    if conversation is not None:
        # 2. Closed/archived conversations are not actively routed; keep mode.
        if conversation.status in (ConversationStatus.CLOSED, ConversationStatus.ARCHIVED):
            return conversation.mode or ConversationMode.MANUAL.value
        # 3. Explicit pause wins over AI classification.
        if conversation.mode == ConversationMode.PAUSED:
            return ConversationMode.PAUSED.value
        # 4. AI disabled => manual.
        if not conversation.ai_enabled:
            return ConversationMode.MANUAL.value

    # 5-7. Classify by contact type.
    if contact.type == ContactType.CLIENT:
        return ConversationMode.SUPPORT_AI.value
    if contact.type == ContactType.LEAD:
        return ConversationMode.SALES_AI.value
    if contact.type == ContactType.INTERNAL:
        return ConversationMode.INTERNAL_ASSISTANT.value

    # 8. Safe fallback.
    return ConversationMode.MANUAL.value


class ConversationRouter:
    """Namespaced access to :func:`route` for discoverability."""

    @staticmethod
    def route(contact, conversation=None) -> str:
        return route(contact, conversation)
