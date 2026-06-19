"""Provider interface. SDK types never leak past this boundary."""

from abc import ABC, abstractmethod

from crm.ai.domain.value_objects import AIRequest, AIResponse


class BaseAIProvider(ABC):
    """All providers normalize requests/responses to AIRequest/AIResponse."""

    provider_type: str = ""

    def __init__(
        self, *, model_name: str, temperature: float, max_tokens: int, timeout_seconds: int
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def generate_text(self, request: AIRequest) -> AIResponse: ...

    @abstractmethod
    def generate_structured(self, request: AIRequest) -> AIResponse: ...

    @abstractmethod
    def generate_with_tools(self, request: AIRequest) -> AIResponse: ...

    def transcribe_audio(self, request: AIRequest) -> AIResponse:
        raise NotImplementedError(f"{self.provider_type} does not support audio transcription")

    def generate_image(self, request: AIRequest) -> AIResponse:
        raise NotImplementedError(f"{self.provider_type} does not support image generation")

    def create_embedding(self, request: AIRequest) -> AIResponse:
        raise NotImplementedError(f"{self.provider_type} does not support embeddings")
