from django.db import transaction
from django.utils.text import slugify

from crm.core.security.permissions import Role
from crm.organizations.models import Membership, Organization


def unique_slug_for_name(name: str) -> str:
    base_slug = slugify(name) or "organization"
    candidate = base_slug
    suffix = 1
    while Organization.objects.filter(slug=candidate).exists():
        suffix += 1
        candidate = f"{base_slug}-{suffix}"
    return candidate


@transaction.atomic
def create_organization_for_user(
    *,
    owner,
    name: str,
    slug: str | None = None,
    role: str = Role.OWNER.value,
) -> Organization:
    organization = Organization.objects.create(
        name=name,
        slug=slug or unique_slug_for_name(name),
        owner=owner,
        organization_id=None,
    )
    organization.organization_id = organization.id
    organization.save(update_fields=["organization_id", "updated_at"])
    Membership.objects.create(
        organization=organization,
        organization_id=organization.id,
        user=owner,
        role=role,
        status=Membership.Status.ACTIVE,
    )
    return organization
