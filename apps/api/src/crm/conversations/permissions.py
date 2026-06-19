"""DRF permission classes for conversations, built on Phase 2's RequiresPermission."""

from crm.core.security.drf import RequiresPermission
from crm.core.security.permissions import PermissionCode


class ConversationViewPermission(RequiresPermission):
    required_permission = PermissionCode.CONVERSATIONS_VIEW.value


class ConversationReplyPermission(RequiresPermission):
    required_permission = PermissionCode.CONVERSATIONS_REPLY.value


class ConversationTakeoverPermission(RequiresPermission):
    required_permission = PermissionCode.CONVERSATIONS_TAKEOVER.value
