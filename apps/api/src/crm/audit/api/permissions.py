from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode


class AuditReadPermission(RequiresPermission):
    required_permission = PermissionCode.AUDIT_VIEW.value
