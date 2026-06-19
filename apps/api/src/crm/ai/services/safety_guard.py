"""SafetyGuard: deterministic gate for every AI reply bound for a human.

Safety never depends solely on a model. These rules run BEFORE any outbound
send and decide: send / revise / ask_clarifying_question / handoff_to_human /
do_not_reply / notify_owner. Rule order = severity order (worst wins).
"""

from crm.ai.domain import policies
from crm.ai.domain.enums import RiskLevel, SafetyDecision, max_risk
from crm.ai.domain.value_objects import SafetyResult
from crm.business_settings.models import SalesPolicy


class SensitiveDataDetector:
    @staticmethod
    def find(text: str) -> list[str]:
        hits: list[str] = []
        for pattern in policies.SENSITIVE_DATA_PATTERNS:
            for match in pattern.findall(text or ""):
                hits.append(str(match)[:32])
        return hits


class PolicyChecker:
    """Organization policy checks (currently: price quoting authorization)."""

    @staticmethod
    def unauthorized_price(organization_id, reply: str) -> bool:
        if not policies.PRICE_PATTERN.search(reply or ""):
            return False
        policy = SalesPolicy.objects.filter(organization_id=organization_id).first()
        return policy is None or not policy.can_quote_prices


class ReplyValidator:
    @staticmethod
    def password_request(reply: str) -> list[str]:
        return [
            match.group(0)
            for pattern in policies.PASSWORD_REQUEST_PATTERNS
            if (match := pattern.search(reply or ""))
        ]

    @staticmethod
    def false_promises(reply: str) -> list[str]:
        return [
            match.group(0)
            for pattern in policies.FALSE_PROMISE_PATTERNS
            if (match := pattern.search(reply or ""))
        ]


class HandoffPolicy:
    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> list[str]:
        lowered = (text or "").lower()
        return [keyword for keyword in keywords if keyword in lowered]

    @classmethod
    def legal_threat(cls, inbound: str) -> list[str]:
        return cls._contains_any(inbound, policies.LEGAL_THREAT_KEYWORDS)

    @classmethod
    def angry_client(cls, inbound: str) -> list[str]:
        return cls._contains_any(inbound, policies.ANGRY_KEYWORDS)

    @classmethod
    def critical_failure(cls, inbound: str) -> list[str]:
        return cls._contains_any(inbound, policies.CRITICAL_FAILURE_KEYWORDS)

    @classmethod
    def sensitive_operation(cls, inbound: str) -> list[str]:
        return cls._contains_any(inbound, policies.SENSITIVE_OPERATION_KEYWORDS)


class SafetyGuard:
    @staticmethod
    def evaluate_reply(
        *,
        organization_id,
        proposed_reply: str,
        inbound_text: str = "",
        purpose: str = "",
        model_risk_level: str = RiskLevel.LOW.value,
        model_requests_handoff: bool = False,
    ) -> SafetyResult:
        reasons: list[str] = []
        blocked_phrases: list[str] = []
        violations: list[str] = []
        decision = SafetyDecision.SEND.value
        risk = RiskLevel.LOW.value
        notify_owner = False
        handoff = False

        def escalate(new_decision: str, new_risk: str, reason: str) -> None:
            nonlocal decision, risk
            reasons.append(reason)
            risk = max_risk(risk, new_risk)
            order = [
                SafetyDecision.SEND.value,
                SafetyDecision.REVISE.value,
                SafetyDecision.ASK_CLARIFYING_QUESTION.value,
                SafetyDecision.NOTIFY_OWNER.value,
                SafetyDecision.HANDOFF_TO_HUMAN.value,
                SafetyDecision.DO_NOT_REPLY.value,
            ]
            if order.index(new_decision) > order.index(decision):
                decision = new_decision

        # 1. Password / credential request in OUR reply -> block.
        password_hits = ReplyValidator.password_request(proposed_reply)
        if password_hits:
            blocked_phrases.extend(password_hits)
            violations.append("password_request")
            escalate(
                SafetyDecision.DO_NOT_REPLY.value,
                RiskLevel.CRITICAL.value,
                "La respuesta pide credenciales",
            )

        # 2. Guaranteed-result promises -> block.
        promise_hits = ReplyValidator.false_promises(proposed_reply)
        if promise_hits:
            blocked_phrases.extend(promise_hits)
            violations.append("false_promise")
            escalate(
                SafetyDecision.DO_NOT_REPLY.value,
                RiskLevel.HIGH.value,
                "La respuesta promete resultados garantizados",
            )

        # 3. Unauthorized price -> revise (block-by-default posture).
        if PolicyChecker.unauthorized_price(organization_id, proposed_reply):
            violations.append("unauthorized_price")
            escalate(
                SafetyDecision.REVISE.value,
                RiskLevel.HIGH.value,
                "La respuesta menciona precios sin política de precios autorizada",
            )

        # 4. Legal threat in inbound -> handoff.
        legal_hits = HandoffPolicy.legal_threat(inbound_text)
        if legal_hits:
            violations.append("legal_threat")
            escalate(
                SafetyDecision.HANDOFF_TO_HUMAN.value,
                RiskLevel.CRITICAL.value,
                f"Amenaza legal detectada: {', '.join(legal_hits[:3])}",
            )

        # 5. Angry client -> handoff.
        angry_hits = HandoffPolicy.angry_client(inbound_text)
        if angry_hits:
            violations.append("angry_client")
            escalate(
                SafetyDecision.HANDOFF_TO_HUMAN.value,
                RiskLevel.HIGH.value,
                "Cliente muy enojado; requiere atención humana",
            )

        # 6. Critical production failure -> notify owner + handoff.
        critical_hits = HandoffPolicy.critical_failure(inbound_text)
        if critical_hits:
            violations.append("critical_failure")
            notify_owner = True
            escalate(
                SafetyDecision.HANDOFF_TO_HUMAN.value,
                RiskLevel.CRITICAL.value,
                "Fallo crítico reportado; notificar al dueño",
            )

        # 7. Sensitive operations (refund/contract/payment) -> handoff + notify.
        sensitive_ops = HandoffPolicy.sensitive_operation(inbound_text)
        if sensitive_ops:
            violations.append("sensitive_operation")
            notify_owner = True
            escalate(
                SafetyDecision.HANDOFF_TO_HUMAN.value,
                RiskLevel.HIGH.value,
                f"Operación sensible: {', '.join(sensitive_ops[:3])}",
            )

        # 8. Sensitive data (cards/CUIT) inside OUR reply -> revise + redact flag.
        sensitive_data = SensitiveDataDetector.find(proposed_reply)
        if sensitive_data:
            violations.append("sensitive_data_in_reply")
            escalate(
                SafetyDecision.REVISE.value,
                RiskLevel.HIGH.value,
                "La respuesta contiene datos sensibles que deben redactarse",
            )

        # 9. Model self-reported risk: honor conservative escalation.
        if model_requests_handoff:
            escalate(
                SafetyDecision.HANDOFF_TO_HUMAN.value,
                max_risk(risk, RiskLevel.MEDIUM.value),
                "El modelo solicitó derivación a humano",
            )
        elif model_risk_level in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value):
            escalate(
                SafetyDecision.REVISE.value,
                model_risk_level,
                "El modelo reportó riesgo alto en su propia respuesta",
            )

        handoff = decision == SafetyDecision.HANDOFF_TO_HUMAN.value
        if notify_owner and decision == SafetyDecision.SEND.value:
            decision = SafetyDecision.NOTIFY_OWNER.value

        return SafetyResult(
            decision=decision,
            risk_level=risk,
            reasons=reasons,
            blocked_phrases=blocked_phrases,
            policy_violations=violations,
            requires_handoff=handoff,
            owner_notification_required=notify_owner,
            confidence=1.0,  # deterministic rules
        )
