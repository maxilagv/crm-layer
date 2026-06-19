"""Normalized error taxonomy for the AI platform.

Business modules depend on these exceptions only — never on SDK exceptions.
Providers translate their SDK errors into this taxonomy at the boundary.
"""


class AIError(Exception):
    """Base for all AI platform errors."""

    code = "ai_error"

    def __init__(self, message: str = "", *, retryable: bool = False):
        super().__init__(message or self.__class__.__name__)
        self.retryable = retryable


class AIProviderError(AIError):
    code = "ai_provider_error"


class AIProviderTimeout(AIProviderError):
    code = "provider_timeout"

    def __init__(self, message: str = "Provider timed out"):
        super().__init__(message, retryable=True)


class AIProviderRateLimited(AIProviderError):
    code = "provider_rate_limited"

    def __init__(self, message: str = "Provider rate limited"):
        super().__init__(message, retryable=True)


class AIProviderUnavailable(AIProviderError):
    code = "provider_unavailable"

    def __init__(self, message: str = "Provider unavailable"):
        super().__init__(message, retryable=True)


class AIProviderAuthenticationError(AIProviderError):
    code = "provider_authentication_error"


class AIProviderInvalidRequest(AIProviderError):
    code = "provider_invalid_request"


class AIProviderSchemaError(AIProviderError):
    code = "provider_schema_error"


class AIProviderSafetyError(AIProviderError):
    code = "provider_safety_error"


class AIProviderUnknownError(AIProviderError):
    code = "provider_unknown_error"


class AIModelConfigMissing(AIError):
    code = "model_config_missing"


class AIPromptMissing(AIError):
    code = "prompt_missing"


class AIPromptRenderError(AIError):
    code = "prompt_render_error"


class AIStructuredOutputInvalid(AIError):
    code = "structured_output_invalid"

    def __init__(self, message: str = "Structured output invalid", *, errors: list | None = None):
        super().__init__(message)
        self.errors = errors or []


class AIToolPermissionDenied(AIError):
    code = "tool_permission_denied"


class AIToolValidationError(AIError):
    code = "tool_validation_error"

    def __init__(self, message: str = "Tool arguments invalid", *, errors: list | None = None):
        super().__init__(message)
        self.errors = errors or []


class AIToolUnavailable(AIError):
    """The tool's backing business module does not exist yet (explicit stub)."""

    code = "tool_module_unavailable"


class AISafetyBlocked(AIError):
    code = "safety_blocked"

    def __init__(self, message: str = "Blocked by safety guard", *, safety_result=None):
        super().__init__(message)
        self.safety_result = safety_result
