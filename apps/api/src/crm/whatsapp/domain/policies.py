from __future__ import annotations

from django.conf import settings

from crm.conversations.constants import MessageType
from crm.whatsapp.domain.enums import WhatsAppMessageType

DEFAULT_GRAPH_API_VERSION = "v23.0"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0
DEFAULT_MEDIA_DOWNLOAD_TIMEOUT_SECONDS = 30.0
MAX_MEDIA_SIZE_BYTES = 25 * 1024 * 1024

MEDIA_MESSAGE_TYPES = {
    WhatsAppMessageType.AUDIO,
    WhatsAppMessageType.IMAGE,
    WhatsAppMessageType.DOCUMENT,
    WhatsAppMessageType.VIDEO,
    WhatsAppMessageType.STICKER,
}

ALLOWED_MEDIA_MIME_PREFIXES = (
    "audio/",
    "image/",
    "video/",
    "application/pdf",
    "text/plain",
)

META_TO_CRM_MESSAGE_TYPE = {
    WhatsAppMessageType.TEXT.value: MessageType.TEXT.value,
    WhatsAppMessageType.AUDIO.value: MessageType.AUDIO.value,
    WhatsAppMessageType.IMAGE.value: MessageType.IMAGE.value,
    WhatsAppMessageType.DOCUMENT.value: MessageType.DOCUMENT.value,
    WhatsAppMessageType.VIDEO.value: MessageType.VIDEO.value,
    WhatsAppMessageType.STICKER.value: MessageType.STICKER.value,
    WhatsAppMessageType.LOCATION.value: MessageType.LOCATION.value,
    WhatsAppMessageType.CONTACT_CARD.value: MessageType.CONTACT_CARD.value,
}


def graph_api_version() -> str:
    return getattr(settings, "WHATSAPP_GRAPH_API_VERSION", DEFAULT_GRAPH_API_VERSION)


def api_base_url() -> str:
    return getattr(settings, "WHATSAPP_API_BASE_URL", "https://graph.facebook.com")


def request_timeout_seconds() -> float:
    return float(
        getattr(settings, "WHATSAPP_REQUEST_TIMEOUT_SECONDS", DEFAULT_REQUEST_TIMEOUT_SECONDS)
    )


def media_download_timeout_seconds() -> float:
    return float(
        getattr(
            settings,
            "WHATSAPP_MEDIA_DOWNLOAD_TIMEOUT_SECONDS",
            DEFAULT_MEDIA_DOWNLOAD_TIMEOUT_SECONDS,
        )
    )


def crm_message_type(meta_message_type: str) -> str:
    return META_TO_CRM_MESSAGE_TYPE.get(meta_message_type, MessageType.SYSTEM.value)
