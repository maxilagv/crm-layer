import hashlib
import hmac
import json

import pytest
from django.test import override_settings
from django.utils import timezone

from crm.conversations.constants import MessageDirection, MessageStatus, MessageType
from crm.conversations.models import Message, MessageAttachment
from crm.whatsapp.clients.media_client import DownloadedMedia, RetrievedMedia
from crm.whatsapp.clients.meta_client import MetaAPIError, MetaMessageResponse
from crm.whatsapp.domain.enums import (
    MediaReferenceStatus,
    OutboundMessageStatus,
    WebhookEventType,
    WhatsAppDeliveryStatus,
    WhatsAppTemplateStatus,
)
from crm.whatsapp.models import (
    WhatsAppInboundMessage,
    WhatsAppMediaReference,
    WhatsAppMessageStatus,
    WhatsAppOutboundMessage,
    WhatsAppTemplate,
    WhatsAppWebhookEvent,
)
from crm.whatsapp.services.media_downloader import download_media_reference
from crm.whatsapp.services.message_status_handler import handle_message_statuses
from crm.whatsapp.services.outbound_message_sender import (
    queue_text_message,
    send_queued_outbound_message,
)
from crm.whatsapp.services.template_sync import sync_templates_for_organization
from crm.whatsapp.services.webhook_processor import process_event
from tests.factories.accounts import UserFactory
from tests.factories.contacts import ContactFactory, ContactPhoneFactory
from tests.factories.conversations import ConversationFactory
from tests.factories.organizations import MembershipFactory, OrganizationFactory
from tests.factories.whatsapp import (
    WhatsAppBusinessAccountFactory,
    WhatsAppPhoneNumberFactory,
    WhatsAppTemplateFactory,
)

APP_SECRET = "test-app-secret"
VERIFY_TOKEN = "verify-me"
PHONE_NUMBER_ID = "123456789"
CONTACT_WA_ID = "5491167890000"
MESSAGE_ID = "wamid.HBgNNTQ5MTE2Nzg5MDAwMBUCABIYFjNFQj"


def _member(role="owner"):
    user = UserFactory(password="correct-password")
    organization = OrganizationFactory(owner=user)
    MembershipFactory(organization=organization, user=user, role=role)
    return user, organization


def _auth(api_client, user, organization):
    api_client.force_authenticate(user=user)
    return {"HTTP_X_ORGANIZATION_ID": str(organization.id)}


def _install_phone_number(organization):
    account = WhatsAppBusinessAccountFactory(owner_organization_id=organization.id)
    return WhatsAppPhoneNumberFactory(
        business_account=account,
        phone_number_id=PHONE_NUMBER_ID,
        display_phone_number="+5491111111111",
    )


def _raw(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _signature(raw_body: bytes) -> str:
    digest = hmac.new(APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _inbound_text_payload(message_id=MESSAGE_ID) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-1",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "5491111111111",
                                "phone_number_id": PHONE_NUMBER_ID,
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Juan Perez"},
                                    "wa_id": CONTACT_WA_ID,
                                }
                            ],
                            "messages": [
                                {
                                    "from": CONTACT_WA_ID,
                                    "id": message_id,
                                    "timestamp": "1710000000",
                                    "text": {"body": "Hola, quiero consultar"},
                                    "type": "text",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def _inbound_audio_payload(media_id="media-audio-1") -> dict:
    payload = _inbound_text_payload(message_id=f"{MESSAGE_ID}.audio")
    message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    message.pop("text")
    message["type"] = "audio"
    message["audio"] = {
        "id": media_id,
        "mime_type": "audio/ogg",
        "sha256": "abc123",
    }
    return payload


def _status_payload(status="delivered", message_id="wamid.outbound.1") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-1",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "5491111111111",
                                "phone_number_id": PHONE_NUMBER_ID,
                            },
                            "statuses": [
                                {
                                    "id": message_id,
                                    "status": status,
                                    "timestamp": "1710000001",
                                    "recipient_id": CONTACT_WA_ID,
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def _failed_status_payload(message_id="wamid.outbound.failed") -> dict:
    payload = _status_payload("failed", message_id)
    status = payload["entry"][0]["changes"][0]["value"]["statuses"][0]
    status["errors"] = [
        {
            "code": 131026,
            "title": "Message undeliverable",
            "message": "Message undeliverable",
        }
    ]
    return payload


@pytest.mark.django_db
@override_settings(WHATSAPP_VERIFY_TOKEN=VERIFY_TOKEN)
def test_webhook_verification_success(api_client):
    response = api_client.get(
        "/api/v1/webhooks/whatsapp/",
        {"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "12345"},
    )

    assert response.status_code == 200
    assert response.content == b"12345"


@pytest.mark.django_db
@override_settings(WHATSAPP_VERIFY_TOKEN=VERIFY_TOKEN)
def test_webhook_verification_failure(api_client):
    response = api_client.get(
        "/api/v1/webhooks/whatsapp/",
        {"hub.mode": "subscribe", "hub.verify_token": "bad", "hub.challenge": "12345"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
@override_settings(WHATSAPP_APP_SECRET=APP_SECRET)
def test_invalid_signature_returns_403(api_client):
    payload = _inbound_text_payload()
    raw_body = _raw(payload)

    response = api_client.post(
        "/api/v1/webhooks/whatsapp/",
        raw_body,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256="sha256=bad",
    )

    assert response.status_code == 403
    assert WhatsAppWebhookEvent.objects.count() == 0


@pytest.mark.django_db(transaction=True)
@override_settings(WHATSAPP_APP_SECRET=APP_SECRET)
def test_webhook_post_saves_raw_event(api_client, monkeypatch):
    _user, organization = _member()
    _install_phone_number(organization)
    calls = []
    monkeypatch.setattr(
        "crm.whatsapp.tasks.process_webhook_event.delay",
        lambda event_id: calls.append(event_id),
    )
    payload = _inbound_text_payload()
    raw_body = _raw(payload)

    response = api_client.post(
        "/api/v1/webhooks/whatsapp/",
        raw_body,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=_signature(raw_body),
    )

    assert response.status_code == 200
    event = WhatsAppWebhookEvent.objects.get()
    assert event.raw_payload == payload
    assert event.signature.startswith("sha256=")
    assert event.organization_id == organization.id
    assert calls == [str(event.id)]


@pytest.mark.django_db(transaction=True)
@override_settings(WHATSAPP_APP_SECRET=APP_SECRET)
def test_duplicate_webhook_is_ignored(api_client, monkeypatch):
    _user, organization = _member()
    _install_phone_number(organization)
    calls = []
    monkeypatch.setattr(
        "crm.whatsapp.tasks.process_webhook_event.delay",
        lambda event_id: calls.append(event_id),
    )
    raw_body = _raw(_inbound_text_payload())
    headers = {"HTTP_X_HUB_SIGNATURE_256": _signature(raw_body)}

    first = api_client.post(
        "/api/v1/webhooks/whatsapp/",
        raw_body,
        content_type="application/json",
        **headers,
    )
    second = api_client.post(
        "/api/v1/webhooks/whatsapp/",
        raw_body,
        content_type="application/json",
        **headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert WhatsAppWebhookEvent.objects.count() == 1
    assert len(calls) == 1


@pytest.mark.django_db
def test_inbound_text_creates_message():
    _user, organization = _member()
    _install_phone_number(organization)
    event = WhatsAppWebhookEvent.objects.create(
        organization_id=organization.id,
        event_id="message:test",
        event_type=WebhookEventType.MESSAGES,
        raw_payload=_inbound_text_payload(),
    )

    process_event(event.id)

    inbound = WhatsAppInboundMessage.objects.get()
    message = Message.objects.get()
    assert inbound.external_message_id == MESSAGE_ID
    assert inbound.crm_message_id == message.id
    assert message.direction == MessageDirection.INBOUND
    assert message.message_type == MessageType.TEXT
    assert message.body == "Hola, quiero consultar"
    assert message.raw_payload["provider"] == "whatsapp"
    assert "entry" not in message.raw_payload


@pytest.mark.django_db(transaction=True)
def test_inbound_audio_creates_media_reference(monkeypatch):
    _user, organization = _member()
    _install_phone_number(organization)
    calls = []
    monkeypatch.setattr(
        "crm.whatsapp.tasks.download_media.delay",
        lambda media_id: calls.append(media_id),
    )
    event = WhatsAppWebhookEvent.objects.create(
        organization_id=organization.id,
        event_id="message:audio",
        event_type=WebhookEventType.MESSAGES,
        raw_payload=_inbound_audio_payload(),
    )

    process_event(event.id)

    media = WhatsAppMediaReference.objects.get()
    attachment = MessageAttachment.objects.get()
    assert media.external_media_id == "media-audio-1"
    assert media.status == MediaReferenceStatus.QUEUED
    assert media.crm_attachment_id == attachment.id
    assert calls == [str(media.id)]


@pytest.mark.django_db(transaction=True)
def test_outbound_message_queued(monkeypatch):
    user, organization = _member()
    _install_phone_number(organization)
    contact = ContactFactory(organization_id=organization.id)
    ContactPhoneFactory(
        contact=contact,
        organization_id=organization.id,
        phone_e164="+5491167890001",
    )
    conversation = ConversationFactory(organization_id=organization.id, contact=contact)
    calls = []
    monkeypatch.setattr(
        "crm.whatsapp.tasks.send_outbound_message.delay",
        lambda outbound_id: calls.append(outbound_id),
    )

    result = queue_text_message(
        organization=organization,
        conversation=conversation,
        contact=contact,
        body="Hola",
        actor=user,
        idempotency_key="idem-1",
    )
    duplicate = queue_text_message(
        organization=organization,
        conversation=conversation,
        contact=contact,
        body="Hola",
        actor=user,
        idempotency_key="idem-1",
    )

    assert result.created is True
    assert duplicate.created is False
    assert result.outbound.status == OutboundMessageStatus.QUEUED
    assert WhatsAppOutboundMessage.objects.count() == 1
    assert calls == [str(result.outbound.id)]


@pytest.mark.django_db
def test_outbound_message_sent(monkeypatch):
    user, organization = _member()
    _install_phone_number(organization)
    contact = ContactFactory(organization_id=organization.id)
    ContactPhoneFactory(
        contact=contact,
        organization_id=organization.id,
        phone_e164="+5491167890002",
    )
    conversation = ConversationFactory(organization_id=organization.id, contact=contact)
    monkeypatch.setattr("crm.whatsapp.tasks.send_outbound_message.delay", lambda _outbound_id: None)
    result = queue_text_message(
        organization=organization,
        conversation=conversation,
        contact=contact,
        body="Hola",
        actor=user,
    )

    class FakeClient:
        def send_text_message(self, **_kwargs):
            return MetaMessageResponse(
                external_message_id="wamid.outbound.1",
                raw_response={"messages": [{"id": "wamid.outbound.1"}]},
            )

    sent = send_queued_outbound_message(result.outbound.id, client=FakeClient())

    assert sent.status == OutboundMessageStatus.SENT
    assert sent.external_message_id == "wamid.outbound.1"
    assert sent.sent_at is not None
    assert Message.objects.get(id=sent.crm_message_id).status == MessageStatus.SENT


@pytest.mark.django_db
def test_message_status_delivered_updates_record():
    _user, organization = _member()
    _install_phone_number(organization)
    outbound = WhatsAppOutboundMessage.objects.create(
        organization_id=organization.id,
        message_type="text",
        body="Hola",
        recipient_phone_e164=CONTACT_WA_ID,
        external_message_id="wamid.outbound.1",
        status=OutboundMessageStatus.SENT,
        sent_at=timezone.now(),
    )
    event = WhatsAppWebhookEvent.objects.create(
        organization_id=organization.id,
        event_id="status:delivered",
        event_type=WebhookEventType.STATUSES,
        raw_payload=_status_payload("delivered", "wamid.outbound.1"),
    )

    handle_message_statuses(event)
    outbound.refresh_from_db()

    assert outbound.status == OutboundMessageStatus.DELIVERED
    assert outbound.delivered_at is not None
    status = WhatsAppMessageStatus.objects.get()
    assert status.status == WhatsAppDeliveryStatus.DELIVERED


@pytest.mark.django_db
def test_failed_status_updates_error_fields():
    _user, organization = _member()
    _install_phone_number(organization)
    outbound = WhatsAppOutboundMessage.objects.create(
        organization_id=organization.id,
        message_type="text",
        body="Hola",
        recipient_phone_e164=CONTACT_WA_ID,
        external_message_id="wamid.outbound.failed",
        status=OutboundMessageStatus.SENT,
        sent_at=timezone.now(),
    )
    event = WhatsAppWebhookEvent.objects.create(
        organization_id=organization.id,
        event_id="status:failed",
        event_type=WebhookEventType.STATUSES,
        raw_payload=_failed_status_payload(),
    )

    handle_message_statuses(event)
    outbound.refresh_from_db()

    assert outbound.status == OutboundMessageStatus.FAILED
    assert outbound.failed_at is not None
    assert outbound.error_code == "131026"
    assert "undeliverable" in outbound.error_message.lower()


@pytest.mark.django_db
def test_failed_message_stores_error_code():
    user, organization = _member()
    _install_phone_number(organization)
    contact = ContactFactory(organization_id=organization.id)
    ContactPhoneFactory(
        contact=contact,
        organization_id=organization.id,
        phone_e164="+5491167890003",
    )
    conversation = ConversationFactory(organization_id=organization.id, contact=contact)
    result = queue_text_message(
        organization=organization,
        conversation=conversation,
        contact=contact,
        body="Hola",
        actor=user,
    )

    class FakeClient:
        def send_text_message(self, **_kwargs):
            raise MetaAPIError("Invalid recipient", code="131026", response_payload={"error": "x"})

    failed = send_queued_outbound_message(result.outbound.id, client=FakeClient())

    assert failed.status == OutboundMessageStatus.FAILED
    assert failed.error_code == "131026"
    assert "Invalid recipient" in failed.error_message


@pytest.mark.django_db
def test_download_media_worker_uses_fake_media_client():
    _user, organization = _member()
    _install_phone_number(organization)
    event = WhatsAppWebhookEvent.objects.create(
        organization_id=organization.id,
        event_id="message:audio-download",
        event_type=WebhookEventType.MESSAGES,
        raw_payload=_inbound_audio_payload(media_id="media-download-1"),
    )
    process_event(event.id)
    media = WhatsAppMediaReference.objects.get(external_media_id="media-download-1")

    class FakeMediaClient:
        def retrieve_media_url(self, media_id):
            assert media_id == "media-download-1"
            return RetrievedMedia(url="https://temporary.example/media", mime_type="audio/ogg")

        def download_media(self, media_url):
            assert media_url == "https://temporary.example/media"
            return DownloadedMedia(content=b"audio-bytes", mime_type="audio/ogg", size_bytes=11)

    downloaded = download_media_reference(media.id, client=FakeMediaClient())

    assert downloaded.status == MediaReferenceStatus.DOWNLOADED
    assert downloaded.size_bytes == 11
    assert "https://temporary.example/media" not in str(downloaded.metadata)


@pytest.mark.django_db
def test_sync_templates_upserts_without_meta_real():
    _user, organization = _member()
    _install_phone_number(organization)

    class FakeTemplateClient:
        def list_templates(self, *, waba_id):
            assert waba_id.startswith("waba-")
            return [
                {
                    "name": "follow_up",
                    "language": "es_AR",
                    "category": "UTILITY",
                    "status": "APPROVED",
                    "components": [{"type": "BODY", "text": "Hola"}],
                }
            ]

    synced = sync_templates_for_organization(
        organization=organization,
        client=FakeTemplateClient(),
    )

    assert synced == 1
    template = WhatsAppTemplate.objects.get(organization_id=organization.id, name="follow_up")
    assert template.language == "es_AR"
    assert template.status == WhatsAppTemplateStatus.APPROVED


@pytest.mark.django_db
def test_send_template_creates_outbound(api_client, monkeypatch):
    user, organization = _member("admin")
    _install_phone_number(organization)
    contact = ContactFactory(organization_id=organization.id)
    ContactPhoneFactory(
        contact=contact,
        organization_id=organization.id,
        phone_e164="+5491167890004",
    )
    conversation = ConversationFactory(organization_id=organization.id, contact=contact)
    WhatsAppTemplateFactory(
        organization_id=organization.id,
        name="follow_up",
        language="es_AR",
        status=WhatsAppTemplateStatus.APPROVED,
    )
    monkeypatch.setattr("crm.whatsapp.tasks.send_outbound_message.delay", lambda _outbound_id: None)

    response = api_client.post(
        "/api/v1/whatsapp/templates/send/",
        {
            "conversation_id": str(conversation.id),
            "contact_id": str(contact.id),
            "template_name": "follow_up",
            "language": "es_AR",
            "components": [],
            "idempotency_key": "tpl-1",
        },
        format="json",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 201
    outbound = WhatsAppOutboundMessage.objects.get()
    assert outbound.template_name == "follow_up"
    assert outbound.status == OutboundMessageStatus.QUEUED


@pytest.mark.django_db
def test_webhook_events_does_not_expose_raw_payload_by_default(api_client):
    user, organization = _member("admin")
    WhatsAppWebhookEvent.objects.create(
        organization_id=organization.id,
        event_id="event-raw",
        event_type=WebhookEventType.UNKNOWN,
        raw_payload={"secret": "payload"},
    )

    response = api_client.get(
        "/api/v1/whatsapp/webhook-events/",
        **_auth(api_client, user, organization),
    )

    assert response.status_code == 200
    assert "raw_payload" not in response.json()["data"][0]
