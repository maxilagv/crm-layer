from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.notifications.api.serializers import (
    NotificationPreferencePatchSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
)
from crm.notifications.selectors.notifications import (
    notification_get_for_organization,
    notifications_for_organization,
)
from crm.notifications.services.notification_preferences import NotificationPreferenceService
from crm.organizations.selectors.organizations import resolve_current_organization


class NotificationsView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(responses={200: NotificationSerializer(many=True)})
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = notifications_for_organization(
            organization,
            recipient_user=request.user,
            status=request.query_params.get("status"),
            notification_type=request.query_params.get("type"),
            ordering=request.query_params.get("ordering", "-created_at"),
        ).prefetch_related("deliveries")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(NotificationSerializer(page, many=True).data)


class NotificationReadView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(request=None, responses={200: NotificationSerializer})
    def post(self, request, notification_id):
        organization = resolve_current_organization(request)
        notification = notification_get_for_organization(organization, notification_id)
        if notification is None or notification.recipient_user_id not in (None, request.user.id):
            raise NotFound("Notification not found in current organization")
        notification.mark_read()
        return success_response(request, NotificationSerializer(notification).data)


class NotificationPreferencesView(APIView):
    permission_classes = [RequiresPermission]
    required_permission = PermissionCode.TASKS_MANAGE.value

    @extend_schema(responses={200: NotificationPreferenceSerializer})
    def get(self, request):
        organization = resolve_current_organization(request)
        preference = NotificationPreferenceService.get_or_create_default(
            organization=organization,
            recipient_user=request.user,
        )
        return success_response(request, NotificationPreferenceSerializer(preference).data)

    @extend_schema(
        request=NotificationPreferencePatchSerializer,
        responses={200: NotificationPreferenceSerializer},
    )
    def patch(self, request):
        organization = resolve_current_organization(request)
        preference = NotificationPreferenceService.get_or_create_default(
            organization=organization,
            recipient_user=request.user,
        )
        serializer = NotificationPreferencePatchSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        preference = NotificationPreferenceService.update(
            preference=preference,
            data=serializer.validated_data,
        )
        return success_response(request, NotificationPreferenceSerializer(preference).data)
