from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode


class NotificationPermission(RequiresPermission):
    required_permission = PermissionCode.TASKS_MANAGE.value
