"""Media permissions built on Phase 2's RequiresPermission.

Coarse mapping (no fine-grained media permission exists yet): reads require
``contacts.view`` (held by viewer+), writes/downloads require ``contacts.update``
(operator+). Image generation create is gated the same as media writes.
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


class MediaReadPermission(RequiresPermission):
    required_permission = PermissionCode.CONTACTS_VIEW.value


class MediaWritePermission(RequiresPermission):
    required_permission = PermissionCode.CONTACTS_UPDATE.value


class MediaAssetsPermission(_MethodScoped):
    method_permissions = {
        "GET": PermissionCode.CONTACTS_VIEW.value,
        "POST": PermissionCode.CONTACTS_UPDATE.value,
    }
