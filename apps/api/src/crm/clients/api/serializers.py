from rest_framework import serializers

from crm.clients.domain.enums import (
    ClientContactRole,
    ClientStatus,
    ServiceStatus,
    ServiceType,
    SupportLevel,
)
from crm.clients.models import Client, ClientContact, ClientService


class ClientContactSerializer(serializers.ModelSerializer):
    contact_display_name = serializers.CharField(source="contact.display_name", read_only=True)

    class Meta:
        model = ClientContact
        fields = [
            "id",
            "contact_id",
            "contact_display_name",
            "role",
            "is_primary",
            "can_request_support",
            "receives_notifications",
            "created_at",
        ]
        read_only_fields = ["id", "contact_display_name", "created_at"]


class ClientServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientService
        fields = [
            "id",
            "name",
            "service_type",
            "status",
            "started_at",
            "ended_at",
            "configuration",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ClientListSerializer(serializers.ModelSerializer):
    contact_display_name = serializers.CharField(source="contact.display_name", read_only=True)

    class Meta:
        model = Client
        fields = [
            "id",
            "contact_id",
            "contact_display_name",
            "display_name",
            "status",
            "service_plan",
            "support_level",
            "onboarding_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ClientDetailSerializer(serializers.ModelSerializer):
    client_contacts = ClientContactSerializer(many=True, read_only=True)
    services = ClientServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Client
        fields = [
            "id",
            "contact_id",
            "company_id",
            "display_name",
            "status",
            "service_plan",
            "support_level",
            "onboarding_status",
            "started_at",
            "ended_at",
            "metadata",
            "client_contacts",
            "services",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ClientCreateSerializer(serializers.Serializer):
    contact_id = serializers.UUIDField()
    display_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    service_plan = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )
    support_level = serializers.ChoiceField(
        choices=SupportLevel.choices, default=SupportLevel.STANDARD
    )


class ClientUpdateSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=255, required=False)
    service_plan = serializers.CharField(max_length=120, required=False, allow_blank=True)
    support_level = serializers.ChoiceField(choices=SupportLevel.choices, required=False)
    status = serializers.ChoiceField(choices=ClientStatus.choices, required=False)
    onboarding_status = serializers.CharField(max_length=16, required=False)


class ClientContactCreateSerializer(serializers.Serializer):
    contact_id = serializers.UUIDField()
    role = serializers.ChoiceField(
        choices=ClientContactRole.choices, default=ClientContactRole.USER
    )
    is_primary = serializers.BooleanField(default=False)
    can_request_support = serializers.BooleanField(default=True)
    receives_notifications = serializers.BooleanField(default=False)


class ClientServiceCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    service_type = serializers.ChoiceField(choices=ServiceType.choices, default=ServiceType.OTHER)
    status = serializers.ChoiceField(choices=ServiceStatus.choices, default=ServiceStatus.ACTIVE)
    configuration = serializers.DictField(required=False, default=dict)
