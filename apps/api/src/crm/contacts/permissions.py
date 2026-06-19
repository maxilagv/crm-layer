"""DRF permission classes for contacts, built on Phase 2's RequiresPermission.

Collection/detail endpoints need a different permission per HTTP method, so the
required permission is selected by method before delegating to the base class
(which resolves the current organization and checks role + API-key scope).
"""

from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode


class _MethodScopedPermission(RequiresPermission):
    method_permissions: dict[str, str] = {}

    def has_permission(self, request, view) -> bool:
        self.required_permission = self.method_permissions.get(request.method)
        if self.required_permission is None:
            return False
        return super().has_permission(request, view)


class ContactsCollectionPermission(_MethodScopedPermission):
    method_permissions = {
        "GET": PermissionCode.CONTACTS_VIEW.value,
        "POST": PermissionCode.CONTACTS_CREATE.value,
    }


class ContactDetailPermission(_MethodScopedPermission):
    method_permissions = {
        "GET": PermissionCode.CONTACTS_VIEW.value,
        "PATCH": PermissionCode.CONTACTS_UPDATE.value,
        "DELETE": PermissionCode.CONTACTS_UPDATE.value,
    }


class ContactWritePermission(RequiresPermission):
    """Notes, tags and merge all require contacts.update."""

    required_permission = PermissionCode.CONTACTS_UPDATE.value
