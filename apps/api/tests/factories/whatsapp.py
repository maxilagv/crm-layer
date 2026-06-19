import uuid

import factory

from crm.whatsapp.domain.enums import (
    OutboundMessageStatus,
    WebhookEventStatus,
    WebhookEventType,
    WhatsAppTemplateCategory,
    WhatsAppTemplateStatus,
)
from crm.whatsapp.models import (
    WhatsAppBusinessAccount,
    WhatsAppInboundMessage,
    WhatsAppMediaReference,
    WhatsAppMessageStatus,
    WhatsAppOutboundMessage,
    WhatsAppPhoneNumber,
    WhatsAppTemplate,
    WhatsAppWebhookEvent,
)
from tests.factories.conversations import ConversationFactory, MessageFactory


class WhatsAppBusinessAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WhatsAppBusinessAccount

    class Params:
        owner_organization_id = factory.LazyFunction(uuid.uuid4)

    organization_id = factory.SelfAttribute("owner_organization_id")
    waba_id = factory.Sequence(lambda n: f"waba-{n}")
    name = factory.Sequence(lambda n: f"WABA {n}")
    owner_organization_id = None


class WhatsAppPhoneNumberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WhatsAppPhoneNumber

    business_account = factory.SubFactory(WhatsAppBusinessAccountFactory)
    organization_id = factory.SelfAttribute("business_account.organization_id")
    phone_number_id = factory.Sequence(lambda n: f"phone-number-{n}")
    display_phone_number = "+5491111111111"
    verified_name = "CRM Layer"


class WhatsAppWebhookEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WhatsAppWebhookEvent

    organization_id = factory.SelfAttribute("phone_number.organization_id")
    event_id = factory.Sequence(lambda n: f"event-{n}")
    event_type = WebhookEventType.MESSAGES
    raw_payload = factory.Dict({})
    signature = "sha256=abc"
    status = WebhookEventStatus.RECEIVED
    phone_number = factory.SubFactory(WhatsAppPhoneNumberFactory)


class WhatsAppInboundMessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WhatsAppInboundMessage

    webhook_event = factory.SubFactory(WhatsAppWebhookEventFactory)
    organization_id = factory.SelfAttribute("webhook_event.organization_id")
    external_message_id = factory.Sequence(lambda n: f"wamid.inbound-{n}")
    message_type = "text"
    body = "Hola"
    raw_message = factory.Dict({})


class WhatsAppOutboundMessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WhatsAppOutboundMessage

    conversation = factory.SubFactory(ConversationFactory)
    contact = factory.SelfAttribute("conversation.contact")
    organization_id = factory.SelfAttribute("conversation.organization_id")
    message_type = "text"
    body = "Hola"
    recipient_phone_e164 = "5491112345678"
    status = OutboundMessageStatus.QUEUED


class WhatsAppMessageStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WhatsAppMessageStatus

    organization_id = factory.SelfAttribute("outbound_message.organization_id")
    outbound_message = factory.SubFactory(WhatsAppOutboundMessageFactory)
    external_message_id = factory.SelfAttribute("outbound_message.external_message_id")
    status = "delivered"
    raw_status = factory.Dict({})


class WhatsAppTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WhatsAppTemplate

    organization_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"follow_up_{n}")
    language = "es_AR"
    category = WhatsAppTemplateCategory.UTILITY
    status = WhatsAppTemplateStatus.APPROVED
    components = factory.List([])


class WhatsAppMediaReferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WhatsAppMediaReference

    organization_id = factory.SelfAttribute("crm_message.organization_id")
    crm_message = factory.SubFactory(MessageFactory)
    external_media_id = factory.Sequence(lambda n: f"media-{n}")
    media_type = "audio"
