"""ai_setup_providers: two-provider routing (OpenAI quality + Gemini free) with roles."""

import pytest
from django.core.management import call_command

from crm.ai.domain.enums import AIProviderType, AIPurpose
from crm.ai.models import AIModelConfig, AIProvider
from tests.factories.organizations import OrganizationFactory


def _active(org, purpose):
    return (
        AIModelConfig.objects.filter(organization_id=org.id, purpose=purpose, is_active=True)
        .select_related("provider", "fallback_provider")
        .first()
    )


@pytest.mark.django_db
def test_dual_setup_with_openai_key(settings):
    settings.OPENAI_API_KEY = "sk-test"
    org = OrganizationFactory()

    call_command("ai_setup_providers", organization_id=str(org.id))

    # Both providers registered + enabled.
    assert AIProvider.objects.filter(
        organization_id=org.id, provider_type=AIProviderType.OPENAI.value, is_enabled=True
    ).exists()
    assert AIProvider.objects.filter(
        organization_id=org.id, provider_type=AIProviderType.GEMINI.value, is_enabled=True
    ).exists()

    # Quality / customer-facing -> OpenAI, with a free Gemini fallback.
    opener = _active(org, AIPurpose.OUTREACH_OPENER.value)
    assert opener.provider.provider_type == AIProviderType.OPENAI.value
    assert opener.model_name == "gpt-4o-mini"
    assert opener.fallback_provider.provider_type == AIProviderType.GEMINI.value
    assert opener.fallback_model == "gemini-2.5-flash"

    # High-volume classification -> free Gemini, no fallback to paid OpenAI.
    qual = _active(org, AIPurpose.PROSPECT_QUALIFICATION.value)
    assert qual.provider.provider_type == AIProviderType.GEMINI.value
    assert qual.fallback_provider is None

    # Modalities only OpenAI covers.
    audio = _active(org, AIPurpose.AUDIO_TRANSCRIPTION.value)
    assert audio.provider.provider_type == AIProviderType.OPENAI.value
    assert audio.model_name == "whisper-1"
    assert audio.supports_audio is True

    image = _active(org, AIPurpose.IMAGE_GENERATION.value)
    assert image.provider.provider_type == AIProviderType.OPENAI.value
    assert image.supports_images is True

    # Embeddings -> free Gemini.
    emb = _active(org, AIPurpose.EMBEDDING.value)
    assert emb.provider.provider_type == AIProviderType.GEMINI.value
    assert emb.supports_embeddings is True

    # Exactly one active config per purpose (all 17 purposes covered).
    assert AIModelConfig.objects.filter(organization_id=org.id, is_active=True).count() == len(
        AIPurpose.values
    )


@pytest.mark.django_db
def test_text_purposes_stay_on_gemini_without_openai_key(settings):
    settings.OPENAI_API_KEY = ""
    org = OrganizationFactory()

    call_command("ai_setup_providers", organization_id=str(org.id))

    # Without the key, OpenAI text purposes fall back to free Gemini as PRIMARY (nothing breaks).
    opener = _active(org, AIPurpose.OUTREACH_OPENER.value)
    assert opener.provider.provider_type == AIProviderType.GEMINI.value
    assert opener.model_name == "gemini-2.5-flash"


@pytest.mark.django_db
def test_setup_is_idempotent(settings):
    settings.OPENAI_API_KEY = "sk-test"
    org = OrganizationFactory()
    call_command("ai_setup_providers", organization_id=str(org.id))
    call_command("ai_setup_providers", organization_id=str(org.id))
    # One active config per purpose, no duplicates.
    assert AIModelConfig.objects.filter(organization_id=org.id, is_active=True).count() == len(
        AIPurpose.values
    )
