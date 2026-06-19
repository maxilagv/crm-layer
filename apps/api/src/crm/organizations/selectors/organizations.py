import uuid

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from crm.core.observability.context import set_organization_context
from crm.organizations.models import Membership, Organization


class OrganizationResolutionError(PermissionDenied):
    pass


def active_memberships_for_user(user):
    return (
        Membership.objects.filter(user=user, status=Membership.Status.ACTIVE)
        .select_related("organization")
        .order_by("organization__name")
    )


def resolve_current_organization(request: HttpRequest) -> Organization:
    if hasattr(request, "current_organization"):
        user = getattr(request, "user", None)
        set_organization_context(
            organization_id=request.current_organization.id,
            user_id=getattr(user, "id", None),
        )
        return request.current_organization

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise OrganizationResolutionError("Authentication required")

    memberships = list(active_memberships_for_user(user))
    user._active_memberships_cache = memberships

    explicit_id = request.headers.get("X-Organization-ID") or request.GET.get("organization_id")
    if explicit_id:
        try:
            organization_id = uuid.UUID(str(explicit_id))
        except ValueError as exc:
            raise OrganizationResolutionError("Invalid organization id") from exc
        for membership in memberships:
            if membership.organization_id == organization_id:
                request.current_organization = membership.organization
                request.current_membership = membership
                set_organization_context(organization_id=organization_id, user_id=user.id)
                return membership.organization
        raise OrganizationResolutionError("No active membership for organization")

    if len(memberships) == 1:
        request.current_organization = memberships[0].organization
        request.current_membership = memberships[0]
        set_organization_context(
            organization_id=memberships[0].organization_id,
            user_id=user.id,
        )
        return memberships[0].organization

    if not memberships:
        raise OrganizationResolutionError("No active organization membership")

    raise OrganizationResolutionError(
        "X-Organization-ID is required for users with multiple organizations"
    )


def current_membership_for_request(request: HttpRequest) -> Membership:
    if hasattr(request, "current_membership"):
        return request.current_membership
    organization = resolve_current_organization(request)
    return Membership.objects.get(
        user=request.user,
        organization=organization,
        status=Membership.Status.ACTIVE,
    )
