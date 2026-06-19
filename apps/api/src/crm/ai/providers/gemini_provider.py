"""Google Gemini via its OpenAI-compatible endpoint.

Reuses the OpenAI SDK pointed at Gemini's compat base URL, so chat completions,
JSON output and embeddings work through the same normalized path. The API key
comes from ``settings.GEMINI_API_KEY``. Audio transcription and image generation
are not exposed through this compatibility layer.
"""

from django.conf import settings

from crm.ai.domain.enums import AIProviderType
from crm.ai.domain.exceptions import AIProviderAuthenticationError
from crm.ai.domain.value_objects import AIRequest, AIResponse

from .openai_provider import OpenAIProvider

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class GeminiProvider(OpenAIProvider):
    provider_type = AIProviderType.GEMINI.value

    @property
    def client(self):
        if self._client is None:
            api_key = getattr(settings, "GEMINI_API_KEY", "")
            if not api_key:
                raise AIProviderAuthenticationError("GEMINI_API_KEY is not configured")
            from openai import OpenAI  # lazy: only loaded when actually used

            self._client = OpenAI(
                api_key=api_key,
                base_url=GEMINI_OPENAI_BASE_URL,
                timeout=self.timeout_seconds,
            )
        return self._client

    # Gemini's compat layer is most reliable with plain JSON-object mode; the
    # gateway already validates against the Pydantic schema and retries.
    def generate_structured(self, request: AIRequest) -> AIResponse:
        return self._completion(request, response_format={"type": "json_object"})

    def generate_with_tools(self, request: AIRequest) -> AIResponse:
        # Prioritise a clean JSON reply over function-calling for the bot loop.
        return self._completion(request, response_format={"type": "json_object"})

    def transcribe_audio(self, request: AIRequest) -> AIResponse:
        raise NotImplementedError(
            "Gemini (OpenAI-compat) no soporta transcripción de audio por esta vía"
        )

    def generate_image(self, request: AIRequest) -> AIResponse:
        raise NotImplementedError(
            "Gemini (OpenAI-compat) no soporta generación de imágenes por esta vía"
        )
