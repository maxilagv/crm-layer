"""RiskClassifier: deterministic risk scoring for ambiguous-but-risky inputs.

This complements SafetyGuard with a coarse signal used to decide
``ask_clarifying_question`` for ambiguous risky messages. Model-driven risk
classification (purpose ``risk_classification``) lives in the gateway and is
ALWAYS combined with these deterministic results — never used alone.
"""

from crm.ai.domain import policies
from crm.ai.domain.enums import RiskLevel, SafetyDecision, max_risk
from crm.ai.domain.value_objects import SafetyResult

_AMBIGUITY_MARKERS = ("?", "no entiendo", "no me queda claro", "como seria", "cómo sería")
_RISKY_TOPICS = ("pago", "factura", "contrato", "reembolso", "legal", "datos", "contraseña")


class RiskClassifier:
    @staticmethod
    def classify_inbound(text: str) -> SafetyResult:
        lowered = (text or "").lower()
        risk = RiskLevel.LOW.value
        reasons: list[str] = []

        risky_topic_hits = [topic for topic in _RISKY_TOPICS if topic in lowered]
        if risky_topic_hits:
            risk = max_risk(risk, RiskLevel.MEDIUM.value)
            reasons.append(f"Tema riesgoso: {', '.join(risky_topic_hits[:3])}")
        if any(keyword in lowered for keyword in policies.LEGAL_THREAT_KEYWORDS):
            risk = max_risk(risk, RiskLevel.CRITICAL.value)
            reasons.append("Posible amenaza legal")
        if any(keyword in lowered for keyword in policies.CRITICAL_FAILURE_KEYWORDS):
            risk = max_risk(risk, RiskLevel.CRITICAL.value)
            reasons.append("Posible incidente crítico")

        ambiguous = any(marker in lowered for marker in _AMBIGUITY_MARKERS)
        if (
            ambiguous
            and risky_topic_hits
            and risk in (RiskLevel.MEDIUM.value, RiskLevel.HIGH.value)
        ):
            return SafetyResult(
                decision=SafetyDecision.ASK_CLARIFYING_QUESTION.value,
                risk_level=risk,
                reasons=[*reasons, "Mensaje ambiguo sobre tema riesgoso: pedir aclaración"],
            )
        return SafetyResult(decision=SafetyDecision.SEND.value, risk_level=risk, reasons=reasons)
