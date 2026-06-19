from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode


class AnalyticsReadPermission(RequiresPermission):
    required_permission = PermissionCode.AUDIT_VIEW.value
