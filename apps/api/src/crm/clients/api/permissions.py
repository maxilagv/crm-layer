"""Client permissions: read = clients.view, write = contacts.update (operator+)."""

from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode


class _MethodScoped(RequiresPermission):
    method_permissions: dict[str, str] = {}

    def has_permission(self, request, view) -> bool:
        self.required_permission = self.method_permissions.get(request.method)
        if self.required_permission is None:
            return False
        return super().has_permission(request, view)


class ClientsPermission(_MethodScoped):
    method_permissions = {
        "GET": PermissionCode.CLIENTS_VIEW.value,
        "POST": PermissionCode.CONTACTS_UPDATE.value,
        "PATCH": PermissionCode.CONTACTS_UPDATE.value,
    }
