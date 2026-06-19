"""quickstart: one-command local setup leaves a usable organization."""

import pytest
from django.core.management import call_command

from crm.ai.domain.enums import AIProviderType
from crm.ai.models import AIModelConfig, AIPrompt, AIProvider
from crm.business_settings.models import BusinessProfile
from crm.core.security.permissions import Role
from crm.organizations.models import Membership


@pytest.mark.django_db
def test_quickstart_sets_up_usable_org():
    call_command(
        "quickstart",
        email="owner@ejemplo.com",
        name="Maxi",
        organization="Mi Estudio",
        password="secret123",
        owner_phone="5491137725766",
    )

    membership = (
        Membership.objects.select_related("organization")
        .filter(user__email="owner@ejemplo.com", role=Role.OWNER.value)
        .first()
    )
    assert membership is not None
    org = membership.organization

    profile = BusinessProfile.objects.get(organization_id=org.id)
    assert profile.business_name == "Mi Estudio"
    assert profile.owner_name == "Maxi"
    assert profile.owner_phone == "5491137725766"

    assert AIProvider.objects.filter(
        organization_id=org.id, provider_type=AIProviderType.GEMINI.value
    ).exists()
    # Gemini wired for the agent purposes + all prompts seeded.
    assert AIModelConfig.objects.filter(organization_id=org.id, is_active=True).count() >= 5
    assert AIPrompt.objects.filter(organization_id=org.id).count() >= 12


@pytest.mark.django_db
def test_quickstart_is_idempotent():
    kwargs = dict(
        email="owner@ejemplo.com",
        name="Maxi",
        organization="Mi Estudio",
        password="secret123",
    )
    call_command("quickstart", **kwargs)
    call_command("quickstart", **kwargs)  # second run must not crash or duplicate the owner
    assert (
        Membership.objects.filter(user__email="owner@ejemplo.com", role=Role.OWNER.value).count()
        == 1
    )
