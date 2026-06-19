import factory
from django.utils.text import slugify

from crm.core.security.permissions import Role
from crm.organizations.models import Membership, Organization
from tests.factories.accounts import UserFactory


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Organization {n}")
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))
    owner = factory.SubFactory(UserFactory)

    @factory.post_generation
    def sync_organization_id(obj, create, _extracted, **_kwargs):
        if create and obj.organization_id != obj.id:
            obj.organization_id = obj.id
            obj.save(update_fields=["organization_id", "updated_at"])


class MembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Membership

    organization = factory.SubFactory(OrganizationFactory)
    user = factory.SubFactory(UserFactory)
    role = Role.VIEWER.value
    status = Membership.Status.ACTIVE
