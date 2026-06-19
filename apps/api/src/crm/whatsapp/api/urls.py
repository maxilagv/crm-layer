from django.urls import path

from crm.whatsapp.api.bridge_views import (
    WhatsAppBridgeDeliveryStatusView,
    WhatsAppBridgeEventView,
    WhatsAppBridgeInboundView,
    WhatsAppBridgeOutboxView,
    WhatsAppBridgeStatusView,
)
from crm.whatsapp.api.connection_views import (
    WhatsAppAccountsView,
    WhatsAppConnectionView,
    WhatsAppPhoneNumbersView,
)
from crm.whatsapp.api.views import (
    WhatsAppOutboundMessagesView,
    WhatsAppTemplateSendView,
    WhatsAppTemplatesView,
    WhatsAppWebhookEventsView,
    WhatsAppWebhookView,
)

urlpatterns = [
    path("webhooks/whatsapp/", WhatsAppWebhookView.as_view(), name="whatsapp-webhook"),
    path("whatsapp/connection/", WhatsAppConnectionView.as_view(), name="whatsapp-connection"),
    path(
        "whatsapp/bridge/inbound/",
        WhatsAppBridgeInboundView.as_view(),
        name="whatsapp-bridge-inbound",
    ),
    path(
        "whatsapp/bridge/event/",
        WhatsAppBridgeEventView.as_view(),
        name="whatsapp-bridge-event",
    ),
    path(
        "whatsapp/bridge/outbox/",
        WhatsAppBridgeOutboxView.as_view(),
        name="whatsapp-bridge-outbox",
    ),
    path(
        "whatsapp/bridge/delivery-status/",
        WhatsAppBridgeDeliveryStatusView.as_view(),
        name="whatsapp-bridge-delivery-status",
    ),
    path(
        "whatsapp/bridge/status/",
        WhatsAppBridgeStatusView.as_view(),
        name="whatsapp-bridge-status",
    ),
    path("whatsapp/accounts/", WhatsAppAccountsView.as_view(), name="whatsapp-accounts"),
    path(
        "whatsapp/phone-numbers/",
        WhatsAppPhoneNumbersView.as_view(),
        name="whatsapp-phone-numbers",
    ),
    path("whatsapp/templates/", WhatsAppTemplatesView.as_view(), name="whatsapp-templates"),
    path(
        "whatsapp/templates/send/",
        WhatsAppTemplateSendView.as_view(),
        name="whatsapp-templates-send",
    ),
    path(
        "whatsapp/outbound-messages/",
        WhatsAppOutboundMessagesView.as_view(),
        name="whatsapp-outbound-messages",
    ),
    path(
        "whatsapp/webhook-events/",
        WhatsAppWebhookEventsView.as_view(),
        name="whatsapp-webhook-events",
    ),
]
