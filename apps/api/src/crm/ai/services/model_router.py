"""ModelRouter: resolve (organization, purpose) -> provider + model config.

Models are never hardcoded in business services; everything resolves from
``AIModelConfig`` rows. Disabled providers are skipped. A fallback route is
returned when configured so the gateway can retry transparently.
"""

from dataclasses import dataclass

from crm.ai.domain.enums import AIPurpose, ModelCapability
from crm.ai.domain.exceptions import AIModelConfigMissing
from crm.ai.models import AIModelConfig, AIProvider

_CAPABILITY_FIELDS = {
    ModelCapability.TOOLS.value: "supports_tools",
    ModelCapability.STRUCTURED_OUTPUTS.value: "supports_structured_outputs",
    ModelCapability.AUDIO.value: "supports_audio",
    ModelCapability.IMAGES.value: "supports_images",
    ModelCapability.EMBEDDINGS.value: "supports_embeddings",
}


@dataclass(frozen=True)
class RoutedModel:
    provider_type: str
    model_name: str
    temperature: float
    max_tokens: int
    timeout_seconds: int
    config: AIModelConfig
    fallback_provider_type: str | None = None
    fallback_model_name: str | None = None

    @property
    def has_fallback(self) -> bool:
        return bool(self.fallback_provider_type and self.fallback_model_name)


class ModelRouter:
    @staticmethod
    def route(
        *,
        organization_id,
        purpose: str,
        required_capabilities: tuple[str, ...] = (),
    ) -> RoutedModel:
        if purpose not in AIPurpose.values:
            raise AIModelConfigMissing(f"Unknown AI purpose '{purpose}'")

        config = (
            AIModelConfig.objects.filter(
                organization_id=organization_id, purpose=purpose, is_active=True
            )
            .select_related("provider", "fallback_provider")
            .order_by("provider__priority", "-updated_at")
            .first()
        )
        if config is None:
            raise AIModelConfigMissing(
                f"No active AIModelConfig for purpose '{purpose}' in this organization"
            )
        provider: AIProvider = config.provider
        if not provider.is_enabled or provider.deleted_at is not None:
            raise AIModelConfigMissing(
                f"Provider '{provider.name}' for purpose '{purpose}' is disabled"
            )

        for capability in required_capabilities:
            field = _CAPABILITY_FIELDS.get(capability)
            if field and not getattr(config, field):
                raise AIModelConfigMissing(
                    f"Model '{config.model_name}' lacks required capability '{capability}'"
                )

        fallback_provider_type = None
        fallback_model_name = None
        fallback_provider = config.fallback_provider
        if (
            fallback_provider is not None
            and fallback_provider.is_enabled
            and fallback_provider.deleted_at is None
            and config.fallback_model
        ):
            fallback_provider_type = fallback_provider.provider_type
            fallback_model_name = config.fallback_model

        return RoutedModel(
            provider_type=provider.provider_type,
            model_name=config.model_name,
            temperature=float(config.temperature),
            max_tokens=config.max_tokens,
            timeout_seconds=config.timeout_seconds,
            config=config,
            fallback_provider_type=fallback_provider_type,
            fallback_model_name=fallback_model_name,
        )
