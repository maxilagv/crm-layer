from rest_framework import serializers

from crm.notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationDigest,
    NotificationPreference,
)


class NotificationDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationDelivery
        fields = [
            "id",
            "channel",
            "status",
            "attempts",
            "sent_at",
            "failed_at",
            "last_error",
            "created_at",
        ]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    deliveries = NotificationDeliverySerializer(many=True, read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient_user_id",
            "type",
            "title",
            "body",
            "priority",
            "status",
            "resource_type",
            "resource_id",
            "metadata",
            "read_at",
            "created_at",
            "deliveries",
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "recipient_user_id",
            "notification_type",
            "channel",
            "is_enabled",
            "quiet_hours_start",
            "quiet_hours_end",
            "max_per_hour",
            "digest_only",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "recipient_user_id", "created_at", "updated_at"]


class NotificationPreferencePatchSerializer(serializers.Serializer):
    is_enabled = serializers.BooleanField(required=False)
    quiet_hours_start = serializers.TimeField(required=False, allow_null=True)
    quiet_hours_end = serializers.TimeField(required=False, allow_null=True)
    max_per_hour = serializers.IntegerField(required=False, min_value=1, max_value=100)
    digest_only = serializers.BooleanField(required=False)


class NotificationDigestSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationDigest
        fields = [
            "id",
            "recipient_user_id",
            "period_start",
            "period_end",
            "status",
            "title",
            "body",
            "notification_count",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields
