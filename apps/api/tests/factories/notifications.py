import uuid

import factory

from crm.notifications.domain.enums import (
    NotificationDeliveryStatus,
    NotificationType,
)
from crm.notifications.models import Notification, NotificationDelivery


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    organization_id = factory.LazyFunction(uuid.uuid4)
    type = NotificationType.SYSTEM_ALERT
    title = factory.Sequence(lambda n: f"Notification {n}")


class NotificationDeliveryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationDelivery

    notification = factory.SubFactory(NotificationFactory)
    organization_id = factory.SelfAttribute("notification.organization_id")
    status = NotificationDeliveryStatus.PENDING
    channel = "dashboard"
