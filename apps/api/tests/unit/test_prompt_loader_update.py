"""PromptLoader.update_organization: adopt repo prompt changes safely."""

import pytest

from crm.ai.models import AIPrompt, AIPromptVersion
from crm.ai.prompts.loader import PROMPT_FOLDERS, PromptLoader
from tests.factories.organizations import OrganizationFactory


@pytest.mark.django_db
def test_update_is_noop_when_in_sync():
    org = OrganizationFactory()
    PromptLoader.seed_organization(org.id)
    assert PromptLoader.update_organization(org.id) == []


@pytest.mark.django_db
def test_update_creates_new_active_version_on_drift():
    org = OrganizationFactory()
    PromptLoader.seed_organization(org.id)
    prompt = AIPrompt.objects.select_related("active_version").get(
        organization_id=org.id, key="sales_agent_v1"
    )
    v1 = prompt.active_version
    # Bypass the active-version immutability guard to simulate repo drift.
    AIPromptVersion.objects.filter(id=v1.id).update(system_prompt="contenido viejo")

    touched = PromptLoader.update_organization(org.id)

    prompt.refresh_from_db()
    assert prompt.active_version_id != v1.id
    assert prompt.active_version.version == v1.version + 1
    assert any("sales_agent_v1" in t for t in touched)
    # Previous version archived, never lost.
    v1.refresh_from_db()
    assert v1.status == "archived"


@pytest.mark.django_db
def test_update_creates_missing_prompts():
    org = OrganizationFactory()
    touched = PromptLoader.update_organization(org.id)
    assert AIPrompt.objects.filter(organization_id=org.id, key="support_agent_v1").exists()
    assert len(touched) == len(PROMPT_FOLDERS)
