import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from crm.whatsapp.domain.enums import WebhookEventType, WhatsAppMessageType


@dataclass(frozen=True)
class ParsedChange:
    value: dict[str, Any]
    field: str = ""


def iter_changes(payload: dict[str, Any]) -> list[ParsedChange]:
    changes: list[ParsedChange] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            if isinstance(value, dict):
                changes.append(ParsedChange(value=value, field=str(change.get("field") or "")))
    return changes


def classify_event_type(payload: dict[str, Any]) -> str:
    has_messages = False
    has_statuses = False
    for change in iter_changes(payload):
        has_messages = has_messages or bool(change.value.get("messages"))
        has_statuses = has_statuses or bool(change.value.get("statuses"))
    if has_messages:
        return WebhookEventType.MESSAGES.value
    if has_statuses:
        return WebhookEventType.STATUSES.value
    return WebhookEventType.UNKNOWN.value


def extract_phone_number_id(payload: dict[str, Any]) -> str:
    for change in iter_changes(payload):
        metadata = change.value.get("metadata") or {}
        phone_number_id = metadata.get("phone_number_id")
        if phone_number_id:
            return str(phone_number_id)
    return ""


def resolve_event_id(payload: dict[str, Any]) -> str:
    for change in iter_changes(payload):
        for message in change.value.get("messages") or []:
            if message.get("id"):
                return f"message:{message['id']}"
        for status in change.value.get("statuses") or []:
            status_id = status.get("id")
            status_name = status.get("status")
            timestamp = status.get("timestamp")
            if status_id:
                return f"status:{status_id}:{status_name or ''}:{timestamp or ''}"
    relevant = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "payload:" + hashlib.sha256(relevant.encode("utf-8")).hexdigest()


def parse_meta_timestamp(value: str | int | None):
    if value in ("", None):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def normalize_message_type(message: dict[str, Any]) -> str:
    message_type = str(message.get("type") or WhatsAppMessageType.UNSUPPORTED.value)
    if message_type == "contacts":
        return WhatsAppMessageType.CONTACT_CARD.value
    allowed = {choice.value for choice in WhatsAppMessageType}
    return message_type if message_type in allowed else WhatsAppMessageType.UNSUPPORTED.value


def extract_message_body(message: dict[str, Any], message_type: str) -> str:
    if message_type == WhatsAppMessageType.TEXT.value:
        return str((message.get("text") or {}).get("body") or "")
    if message_type == WhatsAppMessageType.LOCATION.value:
        location = message.get("location") or {}
        return ", ".join(
            item
            for item in [
                str(location.get("name") or ""),
                str(location.get("address") or ""),
            ]
            if item
        )
    if message_type == WhatsAppMessageType.CONTACT_CARD.value:
        contacts = message.get("contacts") or []
        return str((contacts[0].get("name") or {}).get("formatted_name") or "") if contacts else ""
    media = message.get(message_type) or {}
    return str(media.get("caption") or media.get("filename") or "")


def extract_media_descriptor(message: dict[str, Any], message_type: str) -> dict[str, Any] | None:
    media = message.get(message_type)
    if not isinstance(media, dict) or not media.get("id"):
        return None
    return {
        "external_media_id": str(media.get("id")),
        "mime_type": str(media.get("mime_type") or ""),
        "sha256": str(media.get("sha256") or ""),
        "file_name": str(media.get("filename") or ""),
        "caption": str(media.get("caption") or ""),
    }
