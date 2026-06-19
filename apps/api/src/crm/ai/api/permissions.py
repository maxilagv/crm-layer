"""Permissions for AI admin endpoints, built on Phase 2's RequiresPermission.

Reads (runs, usage, tool calls, eval results) require ``audit.view``.
Mutations (prompts, model configs, evals run, retry) require ``prompts.manage``.
"""

from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode


class AIReadPermission(RequiresPermission):
    required_permission = PermissionCode.AUDIT_VIEW.value


class AIManagePermission(RequiresPermission):
    required_permission = PermissionCode.PROMPTS_MANAGE.value
