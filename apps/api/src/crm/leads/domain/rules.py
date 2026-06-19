from __future__ import annotations

import re
from dataclasses import dataclass

from crm.contacts.constants import ContactStatus, ContactType
from crm.conversations.constants import ConversationMode

from .enums import LeadTemperature

HOT_SCORE_THRESHOLD = 76
WARM_SCORE_THRESHOLD = 31
GOOD_SCORE_THRESHOLD = 56
CRITICAL_SCORE_THRESHOLD = 90


def clamp_score(value: int | float) -> int:
    return max(0, min(100, int(round(value))))


def temperature_for_score(score: int) -> str:
    score = clamp_score(score)
    if score >= CRITICAL_SCORE_THRESHOLD:
        return LeadTemperature.CRITICAL.value
    if score >= HOT_SCORE_THRESHOLD:
        return LeadTemperature.HOT.value
    if score >= WARM_SCORE_THRESHOLD:
        return LeadTemperature.WARM.value
    return LeadTemperature.COLD.value


def can_auto_create_lead(contact, conversation=None, *, explicit: bool = False) -> tuple[bool, str]:
    if contact.status == ContactStatus.BLOCKED or contact.type == ContactType.BLOCKED:
        return False, "blocked_contact"
    if contact.type == ContactType.CLIENT:
        return False, "client_contact"
    if contact.type == ContactType.INTERNAL:
        return False, "internal_contact"
    if conversation is None:
        return explicit, "manual_only_without_conversation"
    if conversation.mode == ConversationMode.SUPPORT_AI:
        return False, "support_conversation"
    if conversation.mode == ConversationMode.MANUAL and not explicit:
        return False, "manual_requires_explicit"
    return True, "allowed"


_PAIN_WORDS = ("problema", "error", "pierdo", "perdiendo", "demora", "manual", "caos")
_URGENCY_WORDS = ("urgente", "hoy", "ya", "rapido", "rápido", "crítico", "critico")
_BUDGET_WORDS = ("presupuesto", "pagar", "precio", "cotizar", "inversión", "inversion")
_AUTHORITY_WORDS = ("soy dueño", "soy el dueño", "decido", "director", "gerente")
_BUSINESS_WORDS = ("ventas", "clientes", "crm", "whatsapp", "automatizar", "leads")
_TECH_WORDS = ("api", "integrar", "sistema", "software", "ticket", "webhook")
_RISK_WORDS = ("gratis", "no me interesa", "spam", "baja")


@dataclass(frozen=True)
class TextSignals:
    pain_clear: int = 0
    urgency: int = 0
    authority: int = 0
    budget_signal: int = 0
    business_fit: int = 0
    engagement: int = 0
    technical_match: int = 0
    risk_penalty: int = 0

    def as_factors(self) -> dict[str, int]:
        return {
            "pain_clear": self.pain_clear,
            "urgency": self.urgency,
            "authority": self.authority,
            "budget_signal": self.budget_signal,
            "business_fit": self.business_fit,
            "engagement": self.engagement,
            "technical_match": self.technical_match,
            "risk_penalty": self.risk_penalty,
        }


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def score_text_signals(text: str, *, message_count: int = 1) -> TextSignals:
    normalized = re.sub(r"\s+", " ", (text or "").lower())
    return TextSignals(
        pain_clear=20 if _contains_any(normalized, _PAIN_WORDS) else 5,
        urgency=15 if _contains_any(normalized, _URGENCY_WORDS) else 5,
        authority=15 if _contains_any(normalized, _AUTHORITY_WORDS) else 5,
        budget_signal=10 if _contains_any(normalized, _BUDGET_WORDS) else 3,
        business_fit=20 if _contains_any(normalized, _BUSINESS_WORDS) else 8,
        engagement=min(10, max(1, message_count * 2)),
        technical_match=10 if _contains_any(normalized, _TECH_WORDS) else 4,
        risk_penalty=20 if _contains_any(normalized, _RISK_WORDS) else 0,
    )


def score_from_factors(factors: dict[str, int]) -> int:
    positive = sum(
        int(factors.get(key, 0))
        for key in (
            "pain_clear",
            "urgency",
            "authority",
            "budget_signal",
            "business_fit",
            "engagement",
            "technical_match",
        )
    )
    penalty = int(factors.get("risk_penalty", 0))
    return clamp_score(positive - penalty)
