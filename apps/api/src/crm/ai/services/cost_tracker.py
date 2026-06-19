"""Estimated cost calculation from a configurable pricing table.

Prices are per 1M tokens (input/output), per audio minute and per image. The
table can be overridden via ``settings.AI_COST_TABLE`` without code changes;
unknown models fall back to a conservative default so cost is never silently
zero. Exact prices can be tuned later — the design point is that every run gets
an estimate now.
"""

from decimal import Decimal

from django.conf import settings

from crm.ai.domain.value_objects import AIUsage

_DEFAULT_TABLE: dict[str, dict[str, str]] = {
    # model prefix -> prices (USD)
    "gpt-4o-mini": {"input_per_m": "0.15", "output_per_m": "0.60"},
    "gpt-4o": {"input_per_m": "2.50", "output_per_m": "10.00"},
    "gpt-4.1": {"input_per_m": "2.00", "output_per_m": "8.00"},
    "o4-mini": {"input_per_m": "1.10", "output_per_m": "4.40"},
    "claude-haiku": {"input_per_m": "0.80", "output_per_m": "4.00"},
    "claude-sonnet": {"input_per_m": "3.00", "output_per_m": "15.00"},
    "claude-opus": {"input_per_m": "15.00", "output_per_m": "75.00"},
    "whisper": {"audio_per_minute": "0.006"},
    "gpt-image": {"per_image": "0.04"},
    "dall-e": {"per_image": "0.04"},
    "text-embedding": {"input_per_m": "0.02", "output_per_m": "0"},
    "fake": {"input_per_m": "0", "output_per_m": "0"},
    "_default": {
        "input_per_m": "1.00",
        "output_per_m": "4.00",
        "per_image": "0.05",
        "audio_per_minute": "0.01",
    },
}

_MILLION = Decimal("1000000")


class CostTracker:
    @staticmethod
    def _table() -> dict[str, dict[str, str]]:
        merged = dict(_DEFAULT_TABLE)
        merged.update(getattr(settings, "AI_COST_TABLE", {}) or {})
        return merged

    @classmethod
    def _prices_for(cls, model: str) -> dict[str, str]:
        table = cls._table()
        model_lower = (model or "").lower()
        for prefix, prices in table.items():
            if prefix != "_default" and model_lower.startswith(prefix):
                return prices
        return table["_default"]

    @classmethod
    def estimate_cost(cls, *, model: str, usage: AIUsage) -> Decimal:
        prices = cls._prices_for(model)
        cost = Decimal("0")
        if usage.input_tokens:
            cost += Decimal(usage.input_tokens) * Decimal(prices.get("input_per_m", "0")) / _MILLION
        if usage.output_tokens:
            cost += (
                Decimal(usage.output_tokens) * Decimal(prices.get("output_per_m", "0")) / _MILLION
            )
        if usage.audio_seconds:
            cost += (
                Decimal(usage.audio_seconds)
                / Decimal("60")
                * Decimal(prices.get("audio_per_minute", "0"))
            )
        if usage.image_count:
            cost += Decimal(usage.image_count) * Decimal(prices.get("per_image", "0"))
        return cost.quantize(Decimal("0.000001"))
