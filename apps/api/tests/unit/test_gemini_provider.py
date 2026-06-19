"""Gemini provider (OpenAI-compat) wiring + setup command."""

import pytest

from crm.ai.domain.exceptions import AIProviderAuthenticationError
from crm.ai.providers.gemini_provider import GeminiProvider
from crm.ai.providers.provider_factory import build_provider


def _build():
    return build_provider(
        provider_type="gemini",
        model_name="gemini-2.0-flash",
        temperature=0.2,
        max_tokens=512,
        timeout_seconds=30,
    )


def test_factory_builds_gemini_provider():
    provider = _build()
    assert isinstance(provider, GeminiProvider)
    assert provider.provider_type == "gemini"


def test_gemini_client_requires_api_key(settings):
    settings.GEMINI_API_KEY = ""
    provider = _build()
    with pytest.raises(AIProviderAuthenticationError):
        _ = provider.client


def test_gemini_client_uses_compat_base_url(settings):
    settings.GEMINI_API_KEY = "test-key"
    provider = _build()
    client = provider.client
    assert "generativelanguage.googleapis.com" in str(client.base_url)


@pytest.mark.django_db
def test_setup_gemini_command_activates_configs():
    from django.core.management import call_command

    from crm.ai.models import AIModelConfig, AIProvider
    from tests.factories.organizations import OrganizationFactory

    org = OrganizationFactory()
    call_command("ai_setup_gemini", organization_id=str(org.id))

    assert AIProvider.objects.filter(
        organization_id=org.id, provider_type="gemini", is_enabled=True
    ).exists()
    sales = AIModelConfig.objects.filter(
        organization_id=org.id, purpose="sales_reply", is_active=True
    ).first()
    assert sales is not None
    assert sales.model_name == "gemini-2.5-flash"
    # Audio transcription is intentionally not configured for Gemini.
    assert not AIModelConfig.objects.filter(
        organization_id=org.id, purpose="audio_transcription", provider=sales.provider
    ).exists()
