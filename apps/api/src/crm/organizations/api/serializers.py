from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from crm.core.security.permissions import permissions_for_role
from crm.organizations.models import Membership, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "status",
            "plan",
            "default_timezone",
            "default_language",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "status", "plan", "created_at", "updated_at"]

    def validate_default_timezone(self, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise serializers.ValidationError("Invalid timezone") from exc
        return value


class MembershipSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ["role", "status", "joined_at", "permissions"]

    def get_permissions(self, obj):
        return sorted(permissions_for_role(obj.role))
