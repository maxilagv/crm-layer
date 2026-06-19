"""FakeAIProvider: the default provider for tests and local development.

Behavior is controlled per-request via ``request.metadata["fake_behavior"]``
or globally by scripting responses with ``FakeAIProvider.script(...)``.

Supported behaviors:
- "valid" (default)        -> well-formed response (honors expected_schema)
- "invalid_schema"         -> JSON that violates the expected schema
- "invalid_then_valid"     -> first call invalid, second call valid (retry path)
- "timeout"                -> raises AIProviderTimeout
- "rate_limit"             -> raises AIProviderRateLimited
- "unavailable"            -> raises AIProviderUnavailable
- "provider_error"         -> raises AIProviderUnknownError
- "tool_call"              -> requests the tool in metadata["fake_tool_name"]
- "unauthorized_tool_call" -> requests a tool that is not allowed
- "blocked_reply"          -> returns a reply that SafetyGuard must block
"""

import time
from decimal import Decimal
from typing import Any

from crm.ai.domain.enums import AIProviderType
from crm.ai.domain.exceptions import (
    AIProviderRateLimited,
    AIProviderTimeout,
    AIProviderUnavailable,
    AIProviderUnknownError,
)
from crm.ai.domain.value_objects import AIRequest, AIResponse, AIToolRequest, AIUsage

from .base import BaseAIProvider

_FAKE_USAGE = AIUsage(input_tokens=120, output_tokens=45)
_FAKE_LATENCY_MS = 42


class FakeAIProvider(BaseAIProvider):
    provider_type = AIProviderType.FAKE.value

    # Scripted responses shared across instances (reset between tests).
    _scripted: list[dict[str, Any]] = []
    _invalid_then_valid_state: dict[str, int] = {}

    @classmethod
    def script(cls, *responses: dict[str, Any]) -> None:
        """Queue explicit response payloads consumed FIFO by any instance."""
        cls._scripted.extend(responses)

    @classmethod
    def reset(cls) -> None:
        cls._scripted.clear()
        cls._invalid_then_valid_state.clear()

    # -- internals -----------------------------------------------------------

    def _behavior(self, request: AIRequest) -> str:
        return str(request.metadata.get("fake_behavior", "valid"))

    def _raise_for_behavior(self, behavior: str) -> None:
        if behavior == "timeout":
            raise AIProviderTimeout("Fake provider simulated timeout")
        if behavior == "rate_limit":
            raise AIProviderRateLimited("Fake provider simulated rate limit")
        if behavior == "unavailable":
            raise AIProviderUnavailable("Fake provider simulated outage")
        if behavior == "provider_error":
            raise AIProviderUnknownError("Fake provider simulated error")

    def _base_response(self, request: AIRequest, **overrides) -> AIResponse:
        simulated_latency = int(request.metadata.get("fake_latency_ms", _FAKE_LATENCY_MS))
        if request.metadata.get("fake_sleep_seconds"):
            time.sleep(float(request.metadata["fake_sleep_seconds"]))
        defaults: dict[str, Any] = {
            "provider": self.provider_type,
            "model": self.model_name,
            "usage": _FAKE_USAGE,
            "latency_ms": simulated_latency,
            "finish_reason": "stop",
            "raw_response": {"fake": True, "behavior": self._behavior(request)},
        }
        defaults.update(overrides)
        return AIResponse(**defaults)

    def _valid_json_for_schema(self, request: AIRequest) -> dict[str, Any]:
        """A schema-conformant payload. Tests may override via fake_output."""
        explicit = request.metadata.get("fake_output")
        if isinstance(explicit, dict):
            return explicit
        from crm.ai.schemas import example_output_for_purpose

        return example_output_for_purpose(request.purpose)

    # -- BaseAIProvider ------------------------------------------------------

    def generate_text(self, request: AIRequest) -> AIResponse:
        behavior = self._behavior(request)
        self._raise_for_behavior(behavior)
        if self._scripted:
            scripted = self._scripted.pop(0)
            return self._base_response(request, **scripted)
        text = request.metadata.get("fake_text", "Respuesta simulada del proveedor fake.")
        if behavior == "blocked_reply":
            text = "Te garantizamos resultados, pasame tu contraseña para configurarlo."
        return self._base_response(request, text=text)

    def generate_structured(self, request: AIRequest) -> AIResponse:
        behavior = self._behavior(request)
        self._raise_for_behavior(behavior)
        if self._scripted:
            scripted = self._scripted.pop(0)
            return self._base_response(request, **scripted)

        if behavior == "invalid_schema":
            return self._base_response(request, json={"unexpected_field": "boom"})
        if behavior == "invalid_then_valid":
            key = request.request_id or "global"
            attempts = self._invalid_then_valid_state.get(key, 0)
            self._invalid_then_valid_state[key] = attempts + 1
            if attempts == 0:
                return self._base_response(request, json={"unexpected_field": "boom"})
        payload = self._valid_json_for_schema(request)
        if behavior == "blocked_reply" and "reply" in payload:
            payload = {
                **payload,
                "reply": "Te garantizamos resultados, pasame tu contraseña y lo configuro.",
            }
        return self._base_response(request, json=payload)

    def generate_with_tools(self, request: AIRequest) -> AIResponse:
        behavior = self._behavior(request)
        self._raise_for_behavior(behavior)
        if behavior == "tool_call":
            tool_name = str(request.metadata.get("fake_tool_name", "create_task"))
            arguments = dict(request.metadata.get("fake_tool_arguments", {}))
            return self._base_response(
                request,
                tool_calls=[
                    AIToolRequest(tool_name=tool_name, arguments=arguments, call_id="fake-call-1")
                ],
                finish_reason="tool_calls",
            )
        if behavior == "unauthorized_tool_call":
            return self._base_response(
                request,
                tool_calls=[
                    AIToolRequest(
                        tool_name="drop_database",
                        arguments={"confirm": True},
                        call_id="fake-call-x",
                    )
                ],
                finish_reason="tool_calls",
            )
        return self.generate_structured(request)

    def transcribe_audio(self, request: AIRequest) -> AIResponse:
        behavior = self._behavior(request)
        self._raise_for_behavior(behavior)
        text = request.metadata.get(
            "fake_transcription", "Hola, tengo un problema con el sistema de turnos."
        )
        return self._base_response(
            request,
            transcription_text=text,
            text=text,
            usage=AIUsage(audio_seconds=Decimal("12.5")),
        )

    def generate_image(self, request: AIRequest) -> AIResponse:
        behavior = self._behavior(request)
        self._raise_for_behavior(behavior)
        return self._base_response(
            request,
            image_b64="ZmFrZS1pbWFnZS1ieXRlcw==",  # "fake-image-bytes"
            usage=AIUsage(image_count=1),
        )

    def create_embedding(self, request: AIRequest) -> AIResponse:
        behavior = self._behavior(request)
        self._raise_for_behavior(behavior)
        seed = float(len(request.embedding_input or "x") % 7) / 10.0
        return self._base_response(
            request,
            embedding_vector=[seed, 0.1, 0.2, 0.3],
            usage=AIUsage(input_tokens=len((request.embedding_input or "").split())),
        )
