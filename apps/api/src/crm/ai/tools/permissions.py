"""ToolPermissionPolicy: server-side authorization for tool execution.

A tool runs only if (a) the purpose is allowed for that tool, and (b) the
acting principal holds every required permission. AI-initiated runs without a
human actor use the AI_AGENT role's permission set from Phase 2.
"""

from crm.ai.domain.exceptions import AIToolPermissionDenied
from crm.core.security.permissions import Role, can, permissions_for_role

from .base import BaseTool, ToolContext


class ToolPermissionPolicy:
    @staticmethod
    def check(*, tool: BaseTool, context: ToolContext) -> None:
        definition = tool.definition

        if definition.allowed_purposes and context.purpose not in definition.allowed_purposes:
            raise AIToolPermissionDenied(
                f"Tool '{definition.name}' is not allowed for purpose '{context.purpose}'"
            )

        if not definition.permissions_required:
            return

        actor = context.actor
        if actor is not None and getattr(actor, "is_authenticated", False):
            organization = _org_stub(context.organization_id)
            for permission in definition.permissions_required:
                if not can(actor, permission, organization):
                    raise AIToolPermissionDenied(
                        f"Actor lacks permission '{permission}' for tool '{definition.name}'"
                    )
            return

        # No human actor: the AI agent role must cover the required permissions.
        ai_permissions = permissions_for_role(Role.AI_AGENT.value)
        for permission in definition.permissions_required:
            if permission not in ai_permissions:
                raise AIToolPermissionDenied(
                    f"AI agent role lacks permission '{permission}' for tool '{definition.name}'"
                )


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()
