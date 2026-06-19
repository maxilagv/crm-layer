"""Settings-facing WhatsApp connection endpoints.

Let an operator (settings.manage) register the WhatsApp Business Account and
phone-number *identifiers* (waba_id / phone_number_id) and inspect connection
status. The secret access token stays in the backend environment
(``WHATSAPP_ACCESS_TOKEN``) — it is never accepted or returned here.
"""

from django.conf import settings as django_settings
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.organizations.selectors.organizations import resolve_current_organization
from crm.whatsapp.models import WhatsAppBusinessAccount, WhatsAppPhoneNumber


class WhatsAppAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppBusinessAccount
        fields = ["id", "waba_id", "name", "status", "created_at"]
        read_only_fields = ["id", "created_at"]


class WhatsAppPhoneNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppPhoneNumber
        fields = [
            "id",
            "business_account_id",
            "phone_number_id",
            "display_phone_number",
            "verified_name",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class WhatsAppPhoneNumberCreateSerializer(serializers.Serializer):
    business_account_id = serializers.UUIDField()
    phone_number_id = serializers.CharField(max_length=64)
    display_phone_number = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default=""
    )
    verified_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )


class _SettingsView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.SETTINGS_MANAGE.value


class WhatsAppAccountsView(_SettingsView):
    def get(self, request):
        organization = resolve_current_organization(request)
        accounts = WhatsAppBusinessAccount.objects.filter(organization_id=organization.id).order_by(
            "-created_at"
        )
        return success_response(request, WhatsAppAccountSerializer(accounts, many=True).data)

    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = WhatsAppAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account, _created = WhatsAppBusinessAccount.objects.update_or_create(
            organization_id=organization.id,
            waba_id=serializer.validated_data["waba_id"],
            defaults={
                "name": serializer.validated_data.get("name", ""),
                "created_by_id": request.user.id,
            },
        )
        return success_response(request, WhatsAppAccountSerializer(account).data, status=201)


class WhatsAppPhoneNumbersView(_SettingsView):
    def get(self, request):
        organization = resolve_current_organization(request)
        numbers = WhatsAppPhoneNumber.objects.filter(organization_id=organization.id).order_by(
            "-created_at"
        )
        return success_response(request, WhatsAppPhoneNumberSerializer(numbers, many=True).data)

    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = WhatsAppPhoneNumberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        account = WhatsAppBusinessAccount.objects.filter(
            organization_id=organization.id, id=data["business_account_id"]
        ).first()
        if account is None:
            raise ValidationError(
                {"business_account_id": "Cuenta de WhatsApp no encontrada en esta organización"}
            )
        number, _created = WhatsAppPhoneNumber.objects.update_or_create(
            organization_id=organization.id,
            phone_number_id=data["phone_number_id"],
            defaults={
                "business_account": account,
                "display_phone_number": data.get("display_phone_number", ""),
                "verified_name": data.get("verified_name", ""),
                "created_by_id": request.user.id,
            },
        )
        return success_response(request, WhatsAppPhoneNumberSerializer(number).data, status=201)


class WhatsAppConnectionView(_SettingsView):
    """Read-only connection status: env credential presence + registered ids."""

    def get(self, request):
        organization = resolve_current_organization(request)
        accounts = WhatsAppBusinessAccount.objects.filter(organization_id=organization.id).count()
        numbers = WhatsAppPhoneNumber.objects.filter(organization_id=organization.id).count()
        credentials = {
            "access_token": bool(getattr(django_settings, "WHATSAPP_ACCESS_TOKEN", "")),
            "verify_token": bool(getattr(django_settings, "WHATSAPP_VERIFY_TOKEN", "")),
            "app_secret": bool(getattr(django_settings, "WHATSAPP_APP_SECRET", "")),
        }
        connected = credentials["access_token"] and numbers > 0
        return success_response(
            request,
            {
                "connected": connected,
                "credentials": credentials,
                "accounts": accounts,
                "phone_numbers": numbers,
                "graph_api_version": getattr(django_settings, "WHATSAPP_GRAPH_API_VERSION", ""),
                "webhook_path": "/api/v1/webhooks/whatsapp/",
                "env_vars": [
                    "WHATSAPP_ACCESS_TOKEN",
                    "WHATSAPP_VERIFY_TOKEN",
                    "WHATSAPP_APP_SECRET",
                ],
            },
        )
