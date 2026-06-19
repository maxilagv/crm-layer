"""Documents permissions (coarse, reusing Phase 2 codes).

Reads require ``contacts.view``; generating/sending requires ``contacts.update``.
The brand kit (branding + fiscal data) requires ``settings.manage``.
"""

from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode


class _MethodScoped(RequiresPermission):
    method_permissions: dict[str, str] = {}

    def has_permission(self, request, view) -> bool:
        self.required_permission = self.method_permissions.get(request.method)
        if self.required_permission is None:
            return False
        return super().has_permission(request, view)


class DocumentsPermission(_MethodScoped):
    method_permissions = {
        "GET": PermissionCode.CONTACTS_VIEW.value,
        "POST": PermissionCode.CONTACTS_UPDATE.value,
    }


class DocumentReadPermission(RequiresPermission):
    required_permission = PermissionCode.CONTACTS_VIEW.value


class DocumentWritePermission(RequiresPermission):
    required_permission = PermissionCode.CONTACTS_UPDATE.value


class BrandKitPermission(RequiresPermission):
    required_permission = PermissionCode.SETTINGS_MANAGE.value
