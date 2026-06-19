"""Owner notifications (e.g. task reminders) reach WhatsApp via the bridge outbox."""

import uuid
from types import SimpleNamespace

import pytest

from crm.notifications.outbox_handlers import handle_owner_whatsapp_message
from crm.whatsapp.models import OutboundMessage
from tests.factories.organizations import OrganizationFactory


def _event(org, body="Recordatorio: llamar a Juan", delivery_id=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=org.id,
        payload={
            "data": {
                "body": body,
                "delivery_id": delivery_id or str(uuid.uuid4()),
            }
        },
    )


@pytest.mark.django_db
def test_owner_notification_enqueues_outbound_and_is_idempotent(settings):
    settings.OWNER_WHATSAPP_NUMBER = "5491137725766"
    org = OrganizationFactory()
    event = _event(org)

    handle_owner_whatsapp_message(event)
    msgs = OutboundMessage.objects.filter(organization_id=org.id)
    assert msgs.count() == 1
    assert "Recordatorio" in msgs.first().body

    # Same delivery → no duplicate send.
    handle_owner_whatsapp_message(event)
    assert OutboundMessage.objects.filter(organization_id=org.id).count() == 1


@pytest.mark.django_db
def test_owner_notification_noop_without_phone(settings):
    settings.OWNER_WHATSAPP_NUMBER = ""
    org = OrganizationFactory()
    handle_owner_whatsapp_message(_event(org))
    assert OutboundMessage.objects.filter(organization_id=org.id).count() == 0


@pytest.mark.django_db
def test_owner_notification_skips_empty_body(settings):
    settings.OWNER_WHATSAPP_NUMBER = "5491137725766"
    org = OrganizationFactory()
    handle_owner_whatsapp_message(_event(org, body="   "))
    assert OutboundMessage.objects.filter(organization_id=org.id).count() == 0


@pytest.mark.django_db
def test_ai_owner_notification_handler_creates_notification():
    from types import SimpleNamespace

    from crm.notifications.models import Notification
    from crm.notifications.outbox_handlers import handle_ai_owner_notification
    from tests.factories.accounts import UserFactory

    user = UserFactory()
    org = OrganizationFactory(owner=user)
    event = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=org.id,
        payload={
            "data": {
                "reason": "Lead caliente quiere una llamada ya",
                "urgency": "high",
                "ai_run_id": str(uuid.uuid4()),
            }
        },
    )
    handle_ai_owner_notification(event)
    assert Notification.objects.filter(organization_id=org.id, type="system_alert").exists()
