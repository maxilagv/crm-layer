import uuid

import factory

from crm.ai.domain.enums import AIProviderType, AIPurpose
from crm.ai.models import AIModelConfig, AIProvider, AIRun, AIUsageRecord
from crm.ai.prompts.loader import PromptLoader

_MEDIA_FLAGS = {
    AIPurpose.AUDIO_TRANSCRIPTION.value: {"supports_audio": True},
    AIPurpose.IMAGE_GENERATION.value: {"supports_images": True},
    AIPurpose.EMBEDDING.value: {"supports_embeddings": True},
}


class AIProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AIProvider

    organization_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Provider {n}")
    provider_type = AIProviderType.FAKE
    is_enabled = True
    priority = 100


class AIModelConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AIModelConfig

    provider = factory.SubFactory(AIProviderFactory)
    organization_id = factory.SelfAttribute("provider.organization_id")
    purpose = AIPurpose.SALES_REPLY
    model_name = "fake-model"
    is_active = True
    supports_tools = True
    supports_structured_outputs = True


class AIRunFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AIRun

    organization_id = factory.LazyFunction(uuid.uuid4)
    purpose = AIPurpose.SALES_REPLY
    provider = "fake"
    model = "fake-model"
    status = "success"
    output_json = {"reply": "Hola", "confidence": 0.9}


class AIUsageRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AIUsageRecord

    ai_run = factory.SubFactory(AIRunFactory)
    organization_id = factory.SelfAttribute("ai_run.organization_id")
    provider = "fake"
    model = "fake-model"
    purpose = AIPurpose.SALES_REPLY
    input_tokens = 100
    output_tokens = 50
    estimated_cost = "0.000100"


def setup_ai_organization(organization, *, purposes=None, seed_prompts=True) -> AIProvider:
    """Wire an organization with a fake provider, model configs and prompts."""
    provider = AIProviderFactory(organization_id=organization.id, name="Fake provider")
    for purpose in purposes or AIPurpose.values:
        AIModelConfigFactory(
            provider=provider,
            organization_id=organization.id,
            purpose=purpose,
            **_MEDIA_FLAGS.get(purpose, {}),
        )
    if seed_prompts:
        PromptLoader.seed_organization(organization.id)
    return provider
