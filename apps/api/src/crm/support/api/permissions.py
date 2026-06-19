"""Support permissions: all ticket/known-issue operations require tickets.manage."""

from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode


class SupportPermission(RequiresPermission):
    required_permission = PermissionCode.TICKETS_MANAGE.value
