"""Pure client rules."""

from crm.contacts.constants import ContactStatus, ContactType


def contact_blocks_support(contact) -> bool:
    return contact.status == ContactStatus.BLOCKED or contact.type == ContactType.BLOCKED
