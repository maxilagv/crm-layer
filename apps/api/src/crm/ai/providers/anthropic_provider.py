"""Anthropic provider. Lazy SDK import; injectable client for tests.

Anthropic has no developer role: developer content is appended to the system
prompt. Structured outputs are requested via instruction + JSON parsing; tool
use is normalized to AIToolRequest. No SDK type leaves this module.
"""

import json
import time
from typing import Any

from django.conf import settings

from crm.ai.domain.enums import AIProviderType
from crm.ai.domain.exceptions import AIProviderAuthenticationError
from crm.ai.domain.value_objects import AIRequest, AIResponse, AIToolRequest, AIUsage

from .base import BaseAIProvider
from .provider_errors import normalize_provider_exception

_STOP_REASON_MAP = {
    "end_turn": "stop",
    "max_tokens": "length",
    "tool_use": "tool_calls",
    "stop_sequence": "stop",
}


class AnthropicProvider(BaseAIProvider):
    provider_type = AIProviderType.ANTHROPIC.value

    def __init__(self, *, client=None, **kwargs):
        super().__init__(**kwargs)
        self._client = client

    @property
    def client(self):
        if self._client is None:
            api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
            if not api_key:
                raise AIProviderAuthenticationError("ANTHROPIC_API_KEY is not configured")
            from anthropic import Anthropic  # lazy: only loaded when actually used

            self._client = Anthropic(api_key=api_key, timeout=self.timeout_seconds)
        return self._client

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _split_messages(request: AIRequest) -> tuple[str, list[dict[str, str]]]:
        system_parts: list[str] = []
        chat: list[dict[str, str]] = []
        for message in request.input_messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role in ("system", "developer"):
                system_parts.append(content)
            elif role in ("user", "assistant"):
                chat.append({"role": role, "content": content})
        if not chat:
            chat = [{"role": "user", "content": ""}]
        return "\n\n".join(part for part in system_parts if part), chat

    @staticmethod
    def _usage_from(raw_usage) -> AIUsage:
        if raw_usage is None:
            return AIUsage()
        return AIUsage(
            input_tokens=getattr(raw_usage, "input_tokens", 0) or 0,
            output_tokens=getattr(raw_usage, "output_tokens", 0) or 0,
            cached_tokens=getattr(raw_usage, "cache_read_input_tokens", 0) or 0,
        )

    def _message(self, request: AIRequest, *, tools: list[dict] | None = None) -> AIResponse:
        system, chat = self._split_messages(request)
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": float(self.temperature),
            "messages": chat,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        started = time.monotonic()
        try:
            response = self.client.messages.create(**kwargs)
        except Exception as exc:
            raise normalize_provider_exception(exc) from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        text_parts: list[str] = []
        tool_requests: list[AIToolRequest] = []
        for block in getattr(response, "content", None) or []:
            block_type = getattr(block, "type", "")
            if block_type == "text":
                text_parts.append(getattr(block, "text", "") or "")
            elif block_type == "tool_use":
                tool_requests.append(
                    AIToolRequest(
                        tool_name=getattr(block, "name", ""),
                        arguments=dict(getattr(block, "input", {}) or {}),
                        call_id=getattr(block, "id", "") or "",
                    )
                )
        text = "".join(text_parts)
        parsed_json: dict[str, Any] | None = None
        if request.expected_schema and text:
            try:
                parsed_json = json.loads(text)
            except (TypeError, ValueError):
                parsed_json = None

        stop_reason = getattr(response, "stop_reason", "") or ""
        return AIResponse(
            text=text,
            json=parsed_json,
            tool_calls=tool_requests,
            usage=self._usage_from(getattr(response, "usage", None)),
            provider=self.provider_type,
            model=getattr(response, "model", self.model_name) or self.model_name,
            latency_ms=latency_ms,
            raw_response={"id": getattr(response, "id", ""), "object": "message"},
            finish_reason=_STOP_REASON_MAP.get(stop_reason, stop_reason),
        )

    # -- BaseAIProvider --------------------------------------------------------

    def generate_text(self, request: AIRequest) -> AIResponse:
        return self._message(request)

    def generate_structured(self, request: AIRequest) -> AIResponse:
        if request.expected_schema:
            schema_hint = (
                "Responde EXCLUSIVAMENTE con un JSON valido que cumpla este JSON Schema, "
                "sin texto adicional:\n" + json.dumps(request.expected_schema, ensure_ascii=False)
            )
            request.input_messages = [
                *request.input_messages,
                {"role": "user", "content": schema_hint},
            ]
        return self._message(request)

    def generate_with_tools(self, request: AIRequest) -> AIResponse:
        tools = [
            {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("argument_schema", {"type": "object"}),
            }
            for tool in request.allowed_tools
        ]
        return self._message(request, tools=tools or None)
