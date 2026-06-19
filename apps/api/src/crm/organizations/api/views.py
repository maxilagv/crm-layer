from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from crm.audit.services import audit_event_create
from crm.core.api.responses import success_response
from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode
from crm.organizations.api.serializers import OrganizationSerializer
from crm.organizations.selectors.organizations import resolve_current_organization


class CurrentOrganizationView(APIView):
    permission_classes = [RequiresPermission]

    @extend_schema(responses={200: OrganizationSerializer}, tags=["organizations"])
    def get(self, request):
        organization = resolve_current_organization(request)
        return success_response(request, OrganizationSerializer(organization).data)

    @extend_schema(
        request=OrganizationSerializer,
        responses={200: OrganizationSerializer},
        tags=["organizations"],
    )
    def patch(self, request):
        self.required_permission = PermissionCode.SETTINGS_MANAGE.value
        permission = RequiresPermission()
        if not permission.has_permission(request, self):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Permission denied")

        organization = resolve_current_organization(request)
        before = OrganizationSerializer(organization).data
        serializer = OrganizationSerializer(organization, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        after = OrganizationSerializer(organization).data
        audit_event_create(
            event_type="settings_updated",
            actor=request.user,
            organization=organization,
            request=request,
            resource_type="organizations_organization",
            resource_id=str(organization.id),
            changes={
                key: {"before": before.get(key), "after": after.get(key)}
                for key in after
                if before.get(key) != after.get(key)
            },
        )
        return success_response(request, after)
