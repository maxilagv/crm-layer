"""Translate SDK exceptions into the normalized AI error taxonomy.

Matching is done by exception class NAME (not isinstance) so the SDKs stay
lazy imports and tests can simulate errors with plain stand-in classes.
"""

from crm.ai.domain.exceptions import (
    AIProviderAuthenticationError,
    AIProviderError,
    AIProviderInvalidRequest,
    AIProviderRateLimited,
    AIProviderTimeout,
    AIProviderUnavailable,
    AIProviderUnknownError,
)

_ERROR_NAME_MAP = {
    # OpenAI SDK
    "APITimeoutError": AIProviderTimeout,
    "RateLimitError": AIProviderRateLimited,
    "APIConnectionError": AIProviderUnavailable,
    "InternalServerError": AIProviderUnavailable,
    "AuthenticationError": AIProviderAuthenticationError,
    "PermissionDeniedError": AIProviderAuthenticationError,
    "BadRequestError": AIProviderInvalidRequest,
    "UnprocessableEntityError": AIProviderInvalidRequest,
    "NotFoundError": AIProviderInvalidRequest,
    # Anthropic SDK
    "APIStatusError": AIProviderUnknownError,
    "OverloadedError": AIProviderUnavailable,
    # Generic
    "TimeoutError": AIProviderTimeout,
    "ConnectionError": AIProviderUnavailable,
}


def normalize_provider_exception(exc: Exception) -> AIProviderError:
    """Map any SDK exception to a normalized AIProviderError instance."""
    if isinstance(exc, AIProviderError):
        return exc
    for klass in type(exc).__mro__:
        mapped = _ERROR_NAME_MAP.get(klass.__name__)
        if mapped is not None:
            return mapped(str(exc)[:500])
    return AIProviderUnknownError(str(exc)[:500])
