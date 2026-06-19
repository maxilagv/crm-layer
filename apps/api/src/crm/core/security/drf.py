from rest_framework.permissions import BasePermission

from crm.audit.services import audit_event_create
from crm.core.security.permissions import can
from crm.organizations.selectors.organizations import (
    OrganizationResolutionError,
    resolve_current_organization,
)


class RequiresPermission(BasePermission):
    required_permission: str | None = None

    def has_permission(self, request, view) -> bool:
        permission = getattr(view, "required_permission", self.required_permission)
        if permission is None:
            return bool(request.user and request.user.is_authenticated)
        try:
            organization = resolve_current_organization(request)
        except OrganizationResolutionError:
            audit_event_create(
                event_type="permission_denied",
                actor=getattr(request, "user", None),
                request=request,
                metadata={"permission": permission, "reason": "organization_resolution_failed"},
            )
            return False

        allowed = can(request.user, permission, organization)
        api_key = getattr(request, "api_key", None)
        if api_key is not None:
            allowed = allowed and api_key.has_scope(permission)
        if not allowed:
            audit_event_create(
                event_type="permission_denied",
                actor=request.user,
                organization=organization,
                request=request,
                metadata={"permission": permission},
            )
        return allowed
