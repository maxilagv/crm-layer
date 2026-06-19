from django.db import IntegrityError, transaction

from crm.audit.services import audit_event_create
from crm.core.services.outbox import create_outbox_event
from crm.notifications.domain import events
from crm.notifications.domain.enums import NotificationPriority
from crm.notifications.domain.rules import build_deduplication_key
from crm.notifications.models import Notification

from .notification_router import NotificationRouter


class NotificationService:
    @staticmethod
    @transaction.atomic
    def create(
        *,
        organization,
        notification_type: str,
        title: str,
        body: str = "",
        priority: str = NotificationPriority.MEDIUM.value,
        recipient_user=None,
        resource_type: str = "",
        resource_id=None,
        metadata: dict | None = None,
        deduplication_key: str = "",
        actor=None,
        request=None,
        route: bool = True,
    ):
        key = deduplication_key or build_deduplication_key(
            notification_type=notification_type,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        if key:
            existing = Notification.objects.filter(
                organization_id=organization.id, deduplication_key=key
            ).first()
            if existing is not None:
                return existing, False
        try:
            notification = Notification.objects.create(
                organization_id=organization.id,
                recipient_user=recipient_user or getattr(organization, "owner", None),
                type=notification_type,
                title=title[:255],
                body=body[:4000],
                priority=priority,
                resource_type=resource_type[:64],
                resource_id=resource_id,
                deduplication_key=key,
                metadata=metadata or {},
                created_by_id=getattr(actor, "id", None),
            )
        except IntegrityError:
            return Notification.objects.get(
                organization_id=organization.id, deduplication_key=key
            ), False

        create_outbox_event(
            event_type=events.NOTIFICATION_CREATED,
            organization_id=organization.id,
            payload={
                "notification_id": str(notification.id),
                "type": notification.type,
                "resource_type": resource_type,
                "resource_id": str(resource_id or ""),
            },
        )
        audit_event_create(
            event_type="notification_created",
            actor=actor,
            organization=organization,
            request=request,
            resource_type="notification",
            resource_id=str(notification.id),
            metadata={"type": notification.type, "priority": notification.priority},
        )
        if route:
            NotificationRouter.route(notification=notification, organization=organization)
        return notification, True

    @staticmethod
    def notify_owner(
        *,
        organization,
        notification_type: str,
        title: str,
        body: str = "",
        priority: str = NotificationPriority.HIGH.value,
        resource_type: str = "",
        resource_id=None,
        metadata: dict | None = None,
        deduplication_key: str = "",
        actor=None,
        request=None,
    ):
        return NotificationService.create(
            organization=organization,
            notification_type=notification_type,
            title=title,
            body=body,
            priority=priority,
            recipient_user=getattr(organization, "owner", None),
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            deduplication_key=deduplication_key,
            actor=actor,
            request=request,
        )
