"""FallbackService: retry a failed provider call on the configured fallback.

Only retryable provider errors (timeout, rate limit, unavailable) trigger the
fallback. Returns the response plus whether the fallback was used.
"""

import logging

from crm.ai.domain.exceptions import AIProviderError
from crm.ai.domain.value_objects import AIRequest, AIResponse
from crm.ai.providers.provider_factory import build_provider

from .model_router import RoutedModel

logger = logging.getLogger(__name__)


def call_with_fallback(
    *, route: RoutedModel, request: AIRequest, method_name: str
) -> tuple[AIResponse, bool]:
    primary = build_provider(
        provider_type=route.provider_type,
        model_name=route.model_name,
        temperature=route.temperature,
        max_tokens=route.max_tokens,
        timeout_seconds=route.timeout_seconds,
    )
    try:
        return getattr(primary, method_name)(request), False
    except AIProviderError as exc:
        if not (exc.retryable and route.has_fallback):
            raise
        logger.warning(
            "Primary AI provider failed; using fallback",
            extra={
                "event": "ai.fallback_used",
                "metadata": {
                    "primary": route.provider_type,
                    "fallback": route.fallback_provider_type,
                    "error_code": exc.code,
                },
            },
        )
        fallback = build_provider(
            provider_type=route.fallback_provider_type,
            model_name=route.fallback_model_name,
            temperature=route.temperature,
            max_tokens=route.max_tokens,
            timeout_seconds=route.timeout_seconds,
        )
        return getattr(fallback, method_name)(request), True
