from crm.notifications.domain.enums import NotificationChannelType
from crm.notifications.models import NotificationPreference


class NotificationPreferenceService:
    @staticmethod
    def get_or_create_default(
        *, organization, recipient_user, channel: str = NotificationChannelType.WHATSAPP.value
    ):
        preference, _ = NotificationPreference.objects.get_or_create(
            organization_id=organization.id,
            recipient_user=recipient_user,
            notification_type="",
            channel=channel,
            defaults={"is_enabled": True, "max_per_hour": 5},
        )
        return preference

    @staticmethod
    def update(*, preference, data: dict):
        mutable = [
            "is_enabled",
            "quiet_hours_start",
            "quiet_hours_end",
            "max_per_hour",
            "digest_only",
        ]
        changed = []
        for field in mutable:
            if field in data:
                setattr(preference, field, data[field])
                changed.append(field)
        if changed:
            preference.save(update_fields=[*changed, "updated_at"])
        return preference
