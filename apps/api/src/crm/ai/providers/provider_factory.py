"""Build provider instances from a routed AIModelConfig."""

from crm.ai.domain.enums import AIProviderType
from crm.ai.domain.exceptions import AIModelConfigMissing

from .anthropic_provider import AnthropicProvider
from .base import BaseAIProvider
from .fake_provider import FakeAIProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

_PROVIDERS: dict[str, type[BaseAIProvider]] = {
    AIProviderType.OPENAI.value: OpenAIProvider,
    AIProviderType.ANTHROPIC.value: AnthropicProvider,
    AIProviderType.GEMINI.value: GeminiProvider,
    AIProviderType.FAKE.value: FakeAIProvider,
}


def build_provider(
    *,
    provider_type: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    timeout_seconds: int,
) -> BaseAIProvider:
    provider_class = _PROVIDERS.get(provider_type)
    if provider_class is None:
        raise AIModelConfigMissing(f"Unknown provider type '{provider_type}'")
    return provider_class(
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
    )
