from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from crm.audit.services import audit_event_create
from crm.core.security.permissions import Role
from crm.organizations.models import Membership


def role_can_assign(actor_role: str, target_role: str) -> bool:
    if actor_role == Role.OWNER.value:
        return target_role in {Role.ADMIN.value, Role.OPERATOR.value, Role.VIEWER.value}
    if actor_role == Role.ADMIN.value:
        return target_role in {Role.OPERATOR.value, Role.VIEWER.value}
    return False


@transaction.atomic
def create_user_for_organization(
    *,
    organization,
    actor,
    actor_membership,
    email: str,
    password: str,
    name: str,
    role: str,
    phone: str = "",
    request=None,
):
    if not role_can_assign(actor_membership.role, role):
        raise PermissionDenied("Cannot assign requested role")

    user = get_user_model().objects.create_user(
        email=email,
        password=password,
        name=name,
        phone=phone,
    )
    Membership.objects.create(
        organization=organization,
        organization_id=organization.id,
        user=user,
        role=role,
        status=Membership.Status.ACTIVE,
        created_by_id=getattr(actor, "id", None),
    )
    audit_event_create(
        event_type="user_created",
        actor=actor,
        organization=organization,
        request=request,
        resource_type="accounts_user",
        resource_id=str(user.id),
        changes={"email": user.email, "role": role},
    )
    return user
