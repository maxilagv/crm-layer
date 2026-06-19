from django.contrib.auth import get_user_model

from crm.organizations.models import Membership


def users_for_organization(organization):
    user_ids = Membership.objects.filter(
        organization=organization,
        status=Membership.Status.ACTIVE,
    ).values("user_id")
    return get_user_model().objects.filter(id__in=user_ids).order_by("email")
