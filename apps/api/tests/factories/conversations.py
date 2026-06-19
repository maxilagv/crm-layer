import factory

from crm.conversations.constants import (
    Channel,
    ConversationMode,
    ConversationStatus,
    MemoryType,
    SummaryType,
)
from crm.conversations.models import (
    Conversation,
    ConversationMemory,
    ConversationSummary,
    Message,
    MessageAttachment,
)
from tests.factories.contacts import ContactFactory


class ConversationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Conversation

    contact = factory.SubFactory(ContactFactory)
    organization_id = factory.SelfAttribute("contact.organization_id")
    channel = Channel.WHATSAPP
    status = ConversationStatus.OPEN
    mode = ConversationMode.MANUAL


class MessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Message

    conversation = factory.SubFactory(ConversationFactory)
    contact = factory.SelfAttribute("conversation.contact")
    organization_id = factory.SelfAttribute("conversation.organization_id")
    direction = "inbound"
    message_type = "text"
    body = "Hello"
    normalized_text = "hello"


class MessageAttachmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MessageAttachment

    message = factory.SubFactory(MessageFactory)
    organization_id = factory.SelfAttribute("message.organization_id")
    external_media_id = factory.Sequence(lambda n: f"media-{n}")


class ConversationSummaryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ConversationSummary

    conversation = factory.SubFactory(ConversationFactory)
    organization_id = factory.SelfAttribute("conversation.organization_id")
    summary = factory.Sequence(lambda n: f"Summary {n}")
    summary_type = SummaryType.SHORT


class ConversationMemoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ConversationMemory

    conversation = factory.SubFactory(ConversationFactory)
    contact = factory.SelfAttribute("conversation.contact")
    organization_id = factory.SelfAttribute("conversation.organization_id")
    memory_type = MemoryType.PREFERENCE
    content = factory.Sequence(lambda n: f"Memory {n}")
    importance = 3
