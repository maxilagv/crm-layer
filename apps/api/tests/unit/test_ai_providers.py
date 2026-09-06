"""Provider abstraction tests: fake provider behaviors + SDK normalization
with injected stand-in clients (no real SDK calls, no network)."""

import uuid
from types import SimpleNamespace

import pytest
from django.conf import settings

from crm.ai.domain.enums import AIPurpose
from crm.ai.domain.exceptions import (
    AIProviderRateLimited,
    AIProviderTimeout,
)
from crm.ai.domain.value_objects import AIRequest
from crm.ai.providers.anthropic_provider import AnthropicProvider
from crm.ai.providers.fake_provider import FakeAIProvider
from crm.ai.providers.openai_provider import OpenAIProvider
from crm.ai.providers.provider_errors import normalize_provider_exception


def _request(**metadata) -> AIRequest:
    return AIRequest(
        organization_id=uuid.uuid4(),
        purpose=AIPurpose.SALES_REPLY.value,
        input_messages=[{"role": "user", "content": "hola"}],
        metadata=metadata,
    )


def _fake() -> FakeAIProvider:
    return FakeAIProvider(
        model_name="fake-model", temperature=0.2, max_tokens=256, timeout_seconds=10
    )


@pytest.fixture(autouse=True)
def _reset_fake_provider():
    FakeAIProvider.reset()
    yield
    FakeAIProvider.reset()


def test_fake_provider_returns_valid_response() -> None:
    response = _fake().generate_structured(_request())
    assert response.provider == "fake"
    assert response.json is not None
    assert response.json["intent"]
    assert response.usage.total_tokens > 0
    assert response.latency_ms > 0


def test_fake_provider_can_return_invalid_schema() -> None:
    response = _fake().generate_structured(_request(fake_behavior="invalid_schema"))
    assert response.json == {"unexpected_field": "boom"}


def test_fake_provider_simulates_timeout() -> None:
    with pytest.raises(AIProviderTimeout):
        _fake().generate_text(_request(fake_behavior="timeout"))


def test_fake_provider_simulates_rate_limit() -> None:
    with pytest.raises(AIProviderRateLimited):
        _fake().generate_text(_request(fake_behavior="rate_limit"))


def test_fake_provider_tool_call() -> None:
    response = _fake().generate_with_tools(
        _request(
            fake_behavior="tool_call",
            fake_tool_name="create_task",
            fake_tool_arguments={"title": "Llamar a Juan"},
        )
    )
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "create_task"
    assert response.tool_calls[0].arguments == {"title": "Llamar a Juan"}


def test_fake_provider_transcription_and_image_and_embedding() -> None:
    fake = _fake()
    audio = fake.transcribe_audio(_request())
    assert audio.transcription_text
    assert audio.usage.audio_seconds > 0
    image = fake.generate_image(_request())
    assert image.image_b64
    assert image.usage.image_count == 1
    embedding = fake.create_embedding(_request())
    assert len(embedding.embedding_vector) == settings.AI_EMBEDDING_DIMENSIONS


# ---------------------------------------------------------------- OpenAI


class _OpenAIStubClient:
    """Minimal stand-in mimicking the OpenAI SDK response shapes."""

    def __init__(self, message=None):
        message = message or SimpleNamespace(content="hola!", tool_calls=None)
        usage = SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=20,
            prompt_tokens_details=SimpleNamespace(cached_tokens=10),
        )
        completion = SimpleNamespace(
            id="cmpl-1",
            model="gpt-4o-mini",
            choices=[SimpleNamespace(message=message, finish_reason="stop")],
            usage=usage,
        )
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: completion))


def test_openai_provider_normalizes_text_response() -> None:
    provider = OpenAIProvider(
        client=_OpenAIStubClient(),
        model_name="gpt-4o-mini",
        temperature=0.2,
        max_tokens=256,
        timeout_seconds=10,
    )
    response = provider.generate_text(_request())
    assert response.text == "hola!"
    assert response.provider == "openai"
    assert response.model == "gpt-4o-mini"
    assert response.usage.input_tokens == 100
    assert response.usage.output_tokens == 20
    assert response.usage.cached_tokens == 10
    assert response.finish_reason == "stop"
    # raw_response stays minimal/sanitized: no SDK objects, no message dump.
    assert set(response.raw_response) == {"id", "object"}


def test_openai_provider_normalizes_tool_calls() -> None:
    message = SimpleNamespace(
        content=None,
        tool_calls=[
            SimpleNamespace(
                id="call_1",
                function=SimpleNamespace(name="create_task", arguments='{"title": "X"}'),
            )
        ],
    )
    provider = OpenAIProvider(
        client=_OpenAIStubClient(message=message),
        model_name="gpt-4o-mini",
        temperature=0.2,
        max_tokens=256,
        timeout_seconds=10,
    )
    response = provider.generate_with_tools(_request())
    assert len(response.tool_calls) == 1
    call = response.tool_calls[0]
    assert call.tool_name == "create_task"
    assert call.arguments == {"title": "X"}
    assert call.call_id == "call_1"


# -------------------------------------------------------------- Anthropic


class _AnthropicStubClient:
    def __init__(self):
        response = SimpleNamespace(
            id="msg-1",
            model="claude-haiku",
            content=[
                SimpleNamespace(type="text", text="ok"),
                SimpleNamespace(
                    type="tool_use",
                    id="toolu_1",
                    name="notify_owner",
                    input={"reason": "lead caliente"},
                ),
            ],
            usage=SimpleNamespace(input_tokens=80, output_tokens=15, cache_read_input_tokens=0),
            stop_reason="tool_use",
        )
        self.messages = SimpleNamespace(create=lambda **kwargs: response)


def test_anthropic_provider_normalizes_tool_use() -> None:
    provider = AnthropicProvider(
        client=_AnthropicStubClient(),
        model_name="claude-haiku",
        temperature=0.2,
        max_tokens=256,
        timeout_seconds=10,
    )
    response = provider.generate_with_tools(_request())
    assert response.text == "ok"
    assert response.provider == "anthropic"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "notify_owner"
    assert response.finish_reason == "tool_calls"  # normalized stop reason
    assert response.usage.input_tokens == 80


# ------------------------------------------------------ error normalization


def test_provider_timeout_is_normalized() -> None:
    class APITimeoutError(Exception):  # same name as the SDK class
        pass

    normalized = normalize_provider_exception(APITimeoutError("slow"))
    assert isinstance(normalized, AIProviderTimeout)
    assert normalized.retryable is True


def test_provider_rate_limit_is_normalized() -> None:
    class RateLimitError(Exception):
        pass

    normalized = normalize_provider_exception(RateLimitError("429"))
    assert isinstance(normalized, AIProviderRateLimited)
    assert normalized.retryable is True
