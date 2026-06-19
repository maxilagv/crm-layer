from collections.abc import Iterable
from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    AI_AGENT = "ai_agent"
    SYSTEM = "system"


class PermissionCode(StrEnum):
    CONTACTS_VIEW = "contacts.view"
    CONTACTS_CREATE = "contacts.create"
    CONTACTS_UPDATE = "contacts.update"
    CONVERSATIONS_VIEW = "conversations.view"
    CONVERSATIONS_REPLY = "conversations.reply"
    CONVERSATIONS_TAKEOVER = "conversations.takeover"
    LEADS_VIEW = "leads.view"
    LEADS_UPDATE = "leads.update"
    CLIENTS_VIEW = "clients.view"
    TICKETS_MANAGE = "tickets.manage"
    TASKS_MANAGE = "tasks.manage"
    PROMPTS_MANAGE = "prompts.manage"
    SETTINGS_MANAGE = "settings.manage"
    AUDIT_VIEW = "audit.view"
    PROSPECTING_VIEW = "prospecting.view"
    PROSPECTING_MANAGE = "prospecting.manage"


ALL_PERMISSIONS = frozenset(permission.value for permission in PermissionCode)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    Role.OWNER.value: ALL_PERMISSIONS,
    Role.ADMIN.value: frozenset(
        {
            PermissionCode.CONTACTS_VIEW,
            PermissionCode.CONTACTS_CREATE,
            PermissionCode.CONTACTS_UPDATE,
            PermissionCode.CONVERSATIONS_VIEW,
            PermissionCode.CONVERSATIONS_REPLY,
            PermissionCode.CONVERSATIONS_TAKEOVER,
            PermissionCode.LEADS_VIEW,
            PermissionCode.LEADS_UPDATE,
            PermissionCode.CLIENTS_VIEW,
            PermissionCode.TICKETS_MANAGE,
            PermissionCode.TASKS_MANAGE,
            PermissionCode.PROMPTS_MANAGE,
            PermissionCode.SETTINGS_MANAGE,
            PermissionCode.AUDIT_VIEW,
            PermissionCode.PROSPECTING_VIEW,
            PermissionCode.PROSPECTING_MANAGE,
        }
    ),
    Role.OPERATOR.value: frozenset(
        {
            PermissionCode.CONTACTS_VIEW,
            PermissionCode.CONTACTS_CREATE,
            PermissionCode.CONTACTS_UPDATE,
            PermissionCode.CONVERSATIONS_VIEW,
            PermissionCode.CONVERSATIONS_REPLY,
            PermissionCode.CONVERSATIONS_TAKEOVER,
            PermissionCode.LEADS_VIEW,
            PermissionCode.LEADS_UPDATE,
            PermissionCode.CLIENTS_VIEW,
            PermissionCode.TICKETS_MANAGE,
            PermissionCode.TASKS_MANAGE,
            PermissionCode.PROSPECTING_VIEW,
            PermissionCode.PROSPECTING_MANAGE,
        }
    ),
    Role.VIEWER.value: frozenset(
        {
            PermissionCode.CONTACTS_VIEW,
            PermissionCode.CONVERSATIONS_VIEW,
            PermissionCode.LEADS_VIEW,
            PermissionCode.CLIENTS_VIEW,
            PermissionCode.PROSPECTING_VIEW,
        }
    ),
    Role.AI_AGENT.value: frozenset(
        {
            PermissionCode.CONTACTS_VIEW,
            PermissionCode.CONVERSATIONS_VIEW,
            PermissionCode.CONVERSATIONS_REPLY,
            PermissionCode.LEADS_VIEW,
            PermissionCode.TASKS_MANAGE,
            PermissionCode.TICKETS_MANAGE,
        }
    ),
    Role.SYSTEM.value: frozenset(),
}


def normalize_permission(permission: str | PermissionCode) -> str:
    return permission.value if isinstance(permission, PermissionCode) else permission


def permissions_for_role(role: str) -> frozenset[str]:
    return frozenset(
        permission.value if isinstance(permission, PermissionCode) else permission
        for permission in ROLE_PERMISSIONS.get(role, frozenset())
    )


def permissions_for_roles(roles: Iterable[str]) -> frozenset[str]:
    permissions: set[str] = set()
    for role in roles:
        permissions.update(permissions_for_role(role))
    return frozenset(permissions)


def can(user, permission: str | PermissionCode, organization) -> bool:
    if not user or not getattr(user, "is_authenticated", False) or not organization:
        return False
    if getattr(user, "is_superuser", False):
        return True

    permission_value = normalize_permission(permission)
    memberships = getattr(user, "_active_memberships_cache", None)
    if memberships is None:
        memberships = user.memberships.filter(status="active").select_related("organization")

    for membership in memberships:
        if membership.organization_id == organization.id:
            return permission_value in permissions_for_role(membership.role)
    return False
