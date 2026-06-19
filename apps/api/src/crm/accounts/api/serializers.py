from django.contrib.auth import get_user_model
from rest_framework import serializers

from crm.accounts.models import APIKey
from crm.core.security.permissions import Role, permissions_for_role
from crm.organizations.models import Membership
from crm.organizations.selectors.organizations import current_membership_for_request


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "email",
            "name",
            "phone",
            "timezone",
            "locale",
            "is_staff",
            "is_superuser",
            "is_active",
            "last_login_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(
        choices=[
            (Role.ADMIN.value, Role.ADMIN.value),
            (Role.OPERATOR.value, Role.OPERATOR.value),
            (Role.VIEWER.value, Role.VIEWER.value),
        ],
        default=Role.VIEWER.value,
    )


class UserPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["name", "phone", "timezone", "locale", "is_active"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class TokenPairResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    token_type = serializers.CharField()


class TokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(required=False)


class StatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class APIKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    scopes = serializers.ListField(
        child=serializers.CharField(max_length=120),
        required=False,
        default=list,
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = [
            "id",
            "name",
            "prefix",
            "scopes",
            "last_used_at",
            "expires_at",
            "revoked_at",
            "created_at",
        ]
        read_only_fields = fields


class APIKeyCreatedSerializer(APIKeySerializer):
    key = serializers.CharField()

    class Meta(APIKeySerializer.Meta):
        fields = [*APIKeySerializer.Meta.fields, "key"]


class AuthMeSerializer(serializers.Serializer):
    def to_representation(self, instance):
        request = self.context["request"]
        user = request.user
        membership = current_membership_for_request(request)
        organization = membership.organization
        permissions = sorted(permissions_for_role(membership.role))
        return {
            "user": UserPublicSerializer(user).data,
            "organization": {
                "id": str(organization.id),
                "name": organization.name,
                "slug": organization.slug,
                "status": organization.status,
                "plan": organization.plan,
                "default_timezone": organization.default_timezone,
                "default_language": organization.default_language,
            },
            "membership": {
                "role": membership.role,
                "status": membership.status,
            },
            "memberships": [
                {
                    "organization_id": str(item.organization_id),
                    "organization_name": item.organization.name,
                    "role": item.role,
                    "status": item.status,
                }
                for item in Membership.objects.filter(user=user, status=Membership.Status.ACTIVE)
                .select_related("organization")
                .order_by("organization__name")
            ],
            "permissions": permissions,
            "flags": {
                "can_manage_settings": "settings.manage" in permissions,
                "can_view_audit": "audit.view" in permissions,
            },
        }
