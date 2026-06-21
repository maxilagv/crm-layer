"""Prompt versioning lifecycle + model router + cost tracking tests."""

from decimal import Decimal

import pytest

from crm.ai.domain.enums import AIPurpose, PromptStatus
from crm.ai.domain.exceptions import AIModelConfigMissing, AIPromptRenderError
from crm.ai.domain.value_objects import AIUsage
from crm.ai.models import AIPrompt, PromptVersionImmutableError
from crm.ai.prompts.loader import PromptLoader
from crm.ai.prompts.registry import PromptRegistry
from crm.ai.prompts.renderer import render_template
from crm.ai.services.cost_tracker import CostTracker
from crm.ai.services.model_router import ModelRouter
from crm.audit.models import AuditEvent
from tests.factories.ai import AIModelConfigFactory, AIProviderFactory
from tests.factories.organizations import OrganizationFactory

# ------------------------------------------------------------- versioning


@pytest.mark.django_db
def test_prompt_seed_is_idempotent() -> None:
    organization = OrganizationFactory()
    first = PromptLoader.seed_organization(organization.id)
    second = PromptLoader.seed_organization(organization.id)
    assert len(first) == 17
    assert second == []


@pytest.mark.django_db
def test_prompt_version_activation_archives_previous() -> None:
    organization = OrganizationFactory()
    PromptLoader.seed_organization(organization.id)
    prompt = AIPrompt.objects.get(organization_id=organization.id, key="sales_agent_v1")
    version_one = prompt.active_version
    assert version_one.status == PromptStatus.ACTIVE.value

    draft = PromptRegistry.create_draft(
        prompt=prompt,
        system_prompt="Nuevo system prompt {business_name}",
        template="Mensaje: {current_message}",
        output_schema=version_one.output_schema,
        change_notes="v2",
    )
    assert draft.version == 2
    assert draft.status == PromptStatus.DRAFT.value

    PromptRegistry.activate_version(version=draft)
    prompt.refresh_from_db()
    version_one.refresh_from_db()
    assert prompt.active_version_id == draft.id
    assert version_one.status == PromptStatus.ARCHIVED.value
    assert version_one.archived_at is not None
    # Only one active version per prompt.
    assert prompt.versions.filter(status=PromptStatus.ACTIVE).count() == 1


@pytest.mark.django_db
def test_prompt_activation_is_audited() -> None:
    organization = OrganizationFactory()
    PromptLoader.seed_organization(organization.id)
    assert (
        AuditEvent.objects.filter(
            event_type="ai_prompt_version_activated", organization_id=organization.id
        ).count()
        == 17
    )


@pytest.mark.django_db
def test_active_prompt_version_cannot_be_mutated() -> None:
    organization = OrganizationFactory()
    PromptLoader.seed_organization(organization.id)
    version = AIPrompt.objects.get(
        organization_id=organization.id, key="sales_agent_v1"
    ).active_version
    version.system_prompt = "hackeado"
    with pytest.raises(PromptVersionImmutableError):
        version.save()


def test_prompt_rendering_requires_variables() -> None:
    with pytest.raises(AIPromptRenderError) as excinfo:
        render_template("Hola {nombre}, tu pedido {pedido_id}", {"nombre": "Juan"})
    assert "pedido_id" in str(excinfo.value)


def test_prompt_rendering_injects_json_safely() -> None:
    rendered = render_template("Perfil: {perfil}", {"perfil": {"nombre": "Juan", "x": [1, 2]}})
    assert '"nombre": "Juan"' in rendered


# ----------------------------------------------------------------- router


@pytest.mark.django_db
def test_router_resolves_model_by_purpose() -> None:
    organization = OrganizationFactory()
    provider = AIProviderFactory(organization_id=organization.id)
    AIModelConfigFactory(
        provider=provider,
        organization_id=organization.id,
        purpose=AIPurpose.SALES_REPLY,
        model_name="model-a",
    )
    AIModelConfigFactory(
        provider=provider,
        organization_id=organization.id,
        purpose=AIPurpose.SUPPORT_REPLY,
        model_name="model-b",
    )
    sales = ModelRouter.route(organization_id=organization.id, purpose="sales_reply")
    support = ModelRouter.route(organization_id=organization.id, purpose="support_reply")
    assert sales.model_name == "model-a"
    assert support.model_name == "model-b"


@pytest.mark.django_db
def test_router_rejects_missing_capability() -> None:
    organization = OrganizationFactory()
    provider = AIProviderFactory(organization_id=organization.id)
    AIModelConfigFactory(
        provider=provider,
        organization_id=organization.id,
        purpose=AIPurpose.AUDIO_TRANSCRIPTION,
        supports_audio=False,
    )
    with pytest.raises(AIModelConfigMissing):
        ModelRouter.route(
            organization_id=organization.id,
            purpose="audio_transcription",
            required_capabilities=("audio",),
        )


@pytest.mark.django_db
def test_router_is_tenant_scoped() -> None:
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    AIModelConfigFactory(
        provider=AIProviderFactory(organization_id=org_a.id), organization_id=org_a.id
    )
    with pytest.raises(AIModelConfigMissing):
        ModelRouter.route(organization_id=org_b.id, purpose="sales_reply")


# ------------------------------------------------------------------ costs


def test_cost_tracker_computes_token_costs() -> None:
    cost = CostTracker.estimate_cost(
        model="gpt-4o-mini", usage=AIUsage(input_tokens=1_000_000, output_tokens=1_000_000)
    )
    assert cost == Decimal("0.750000")


def test_cost_tracker_handles_audio_and_images() -> None:
    audio_cost = CostTracker.estimate_cost(
        model="whisper-1", usage=AIUsage(audio_seconds=Decimal("60"))
    )
    assert audio_cost == Decimal("0.006000")
    image_cost = CostTracker.estimate_cost(model="dall-e-3", usage=AIUsage(image_count=2))
    assert image_cost == Decimal("0.080000")


def test_cost_tracker_unknown_model_uses_default_table() -> None:
    cost = CostTracker.estimate_cost(model="some-new-model", usage=AIUsage(input_tokens=1_000_000))
    assert cost == Decimal("1.000000")
