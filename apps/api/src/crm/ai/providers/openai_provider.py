"""OpenAI provider. The SDK is imported lazily; a client can be injected for tests.

API keys come exclusively from ``settings.OPENAI_API_KEY`` (environment).
No SDK type leaves this module: everything is normalized to AIResponse.
"""

import base64
import io
import json
import time
from decimal import Decimal
from typing import Any

from django.conf import settings

from crm.ai.domain.enums import AIProviderType
from crm.ai.domain.exceptions import AIProviderAuthenticationError
from crm.ai.domain.value_objects import AIRequest, AIResponse, AIToolRequest, AIUsage

from .base import BaseAIProvider
from .provider_errors import normalize_provider_exception

# developer role is OpenAI-native; map our roles directly.
_ROLE_MAP = {"system": "system", "developer": "developer", "user": "user", "assistant": "assistant"}


class OpenAIProvider(BaseAIProvider):
    provider_type = AIProviderType.OPENAI.value

    def __init__(self, *, client=None, **kwargs):
        super().__init__(**kwargs)
        self._client = client

    @property
    def client(self):
        if self._client is None:
            api_key = getattr(settings, "OPENAI_API_KEY", "")
            if not api_key:
                raise AIProviderAuthenticationError("OPENAI_API_KEY is not configured")
            from openai import OpenAI  # lazy: only loaded when actually used

            self._client = OpenAI(api_key=api_key, timeout=self.timeout_seconds)
        return self._client

    # -- helpers --------------------------------------------------------------

    def _messages(self, request: AIRequest) -> list[dict[str, str]]:
        return [
            {"role": _ROLE_MAP.get(m.get("role", "user"), "user"), "content": m.get("content", "")}
            for m in request.input_messages
        ]

    @staticmethod
    def _usage_from(raw_usage) -> AIUsage:
        if raw_usage is None:
            return AIUsage()
        cached = 0
        details = getattr(raw_usage, "prompt_tokens_details", None)
        if details is not None:
            cached = getattr(details, "cached_tokens", 0) or 0
        return AIUsage(
            input_tokens=getattr(raw_usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(raw_usage, "completion_tokens", 0) or 0,
            cached_tokens=cached,
        )

    @staticmethod
    def _tool_requests_from(message) -> list[AIToolRequest]:
        requests: list[AIToolRequest] = []
        for call in getattr(message, "tool_calls", None) or []:
            function = getattr(call, "function", None)
            if function is None:
                continue
            try:
                arguments = json.loads(getattr(function, "arguments", "") or "{}")
            except (TypeError, ValueError):
                arguments = {"_unparsed": getattr(function, "arguments", "")}
            requests.append(
                AIToolRequest(
                    tool_name=getattr(function, "name", ""),
                    arguments=arguments,
                    call_id=getattr(call, "id", "") or "",
                )
            )
        return requests

    def _completion(self, request: AIRequest, **extra) -> AIResponse:
        started = time.monotonic()
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=self._messages(request),
                temperature=float(self.temperature),
                max_tokens=self.max_tokens,
                **extra,
            )
        except Exception as exc:
            raise normalize_provider_exception(exc) from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        choice = completion.choices[0]
        message = choice.message
        text = message.content or ""
        parsed_json: dict[str, Any] | None = None
        if extra.get("response_format") and text:
            try:
                parsed_json = json.loads(text)
            except (TypeError, ValueError):
                parsed_json = None

        return AIResponse(
            text=text,
            json=parsed_json,
            tool_calls=self._tool_requests_from(message),
            usage=self._usage_from(getattr(completion, "usage", None)),
            provider=self.provider_type,
            model=getattr(completion, "model", self.model_name) or self.model_name,
            latency_ms=latency_ms,
            raw_response={"id": getattr(completion, "id", ""), "object": "chat.completion"},
            finish_reason=getattr(choice, "finish_reason", "") or "",
        )

    # -- BaseAIProvider --------------------------------------------------------

    def generate_text(self, request: AIRequest) -> AIResponse:
        return self._completion(request)

    def generate_structured(self, request: AIRequest) -> AIResponse:
        response_format: dict[str, Any] = {"type": "json_object"}
        if request.expected_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.metadata.get("schema_name", "output"),
                    "schema": request.expected_schema,
                    "strict": False,
                },
            }
        return self._completion(request, response_format=response_format)

    def generate_with_tools(self, request: AIRequest) -> AIResponse:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("argument_schema", {"type": "object"}),
                },
            }
            for tool in request.allowed_tools
        ]
        extra: dict[str, Any] = {"tools": tools} if tools else {}
        if request.expected_schema:
            extra["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.metadata.get("schema_name", "output"),
                    "schema": request.expected_schema,
                    "strict": False,
                },
            }
        return self._completion(request, **extra)

    def transcribe_audio(self, request: AIRequest) -> AIResponse:
        started = time.monotonic()
        audio_file = io.BytesIO(request.audio_bytes or b"")
        audio_file.name = f"audio.{request.audio_format or 'ogg'}"
        try:
            result = self.client.audio.transcriptions.create(model=self.model_name, file=audio_file)
        except Exception as exc:
            raise normalize_provider_exception(exc) from exc
        latency_ms = int((time.monotonic() - started) * 1000)
        seconds = Decimal(str(getattr(result, "duration", 0) or 0))
        text = getattr(result, "text", "") or ""
        return AIResponse(
            text=text,
            transcription_text=text,
            usage=AIUsage(audio_seconds=seconds),
            provider=self.provider_type,
            model=self.model_name,
            latency_ms=latency_ms,
            raw_response={"object": "transcription"},
            finish_reason="stop",
        )

    def generate_image(self, request: AIRequest) -> AIResponse:
        started = time.monotonic()
        try:
            result = self.client.images.generate(
                model=self.model_name,
                prompt=request.image_prompt,
                n=1,
                response_format="b64_json",
            )
        except Exception as exc:
            raise normalize_provider_exception(exc) from exc
        latency_ms = int((time.monotonic() - started) * 1000)
        item = result.data[0]
        b64 = getattr(item, "b64_json", "") or ""
        url = getattr(item, "url", "") or ""
        if b64:
            # Validate it decodes; never propagate corrupt payloads.
            base64.b64decode(b64, validate=True)
        return AIResponse(
            image_b64=b64,
            image_url=url,
            usage=AIUsage(image_count=1),
            provider=self.provider_type,
            model=self.model_name,
            latency_ms=latency_ms,
            raw_response={"object": "image"},
            finish_reason="stop",
        )

    def create_embedding(self, request: AIRequest) -> AIResponse:
        started = time.monotonic()
        try:
            result = self.client.embeddings.create(
                model=self.model_name, input=request.embedding_input
            )
        except Exception as exc:
            raise normalize_provider_exception(exc) from exc
        latency_ms = int((time.monotonic() - started) * 1000)
        vector = list(result.data[0].embedding)
        return AIResponse(
            embedding_vector=vector,
            usage=self._usage_from(getattr(result, "usage", None)),
            provider=self.provider_type,
            model=self.model_name,
            latency_ms=latency_ms,
            raw_response={"object": "embedding"},
            finish_reason="stop",
        )
