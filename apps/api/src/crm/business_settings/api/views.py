from rest_framework.views import APIView

from crm.business_settings.api.serializers import (
    AIBehaviorPolicySerializer,
    BusinessProfileSerializer,
    NotificationPolicySerializer,
    SalesPolicySerializer,
    SupportPolicySerializer,
    WhatsAppPolicySerializer,
)
from crm.business_settings.models import (
    AIBehaviorPolicy,
    BusinessProfile,
    NotificationPolicy,
    SalesPolicy,
    SupportPolicy,
    WhatsAppPolicy,
)
from crm.business_settings.services.settings import get_or_create_settings, update_settings_record
from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.organizations.selectors.organizations import resolve_current_organization


class SettingsDetailView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.SETTINGS_MANAGE.value
    model = None
    serializer_class = None

    def get(self, request):
        organization = resolve_current_organization(request)
        record = get_or_create_settings(self.model, organization=organization)
        return success_response(request, self.serializer_class(record).data)

    def patch(self, request):
        organization = resolve_current_organization(request)
        record = get_or_create_settings(self.model, organization=organization)
        serializer = self.serializer_class(record, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        record = update_settings_record(
            record=record,
            serializer=serializer,
            actor=request.user,
            organization=organization,
            request=request,
        )
        return success_response(request, self.serializer_class(record).data)


class BusinessProfileView(SettingsDetailView):
    model = BusinessProfile
    serializer_class = BusinessProfileSerializer


class SalesPolicyView(SettingsDetailView):
    model = SalesPolicy
    serializer_class = SalesPolicySerializer


class SupportPolicyView(SettingsDetailView):
    model = SupportPolicy
    serializer_class = SupportPolicySerializer


class AIBehaviorPolicyView(SettingsDetailView):
    model = AIBehaviorPolicy
    serializer_class = AIBehaviorPolicySerializer


class NotificationPolicyView(SettingsDetailView):
    model = NotificationPolicy
    serializer_class = NotificationPolicySerializer


class WhatsAppPolicyView(SettingsDetailView):
    model = WhatsAppPolicy
    serializer_class = WhatsAppPolicySerializer
