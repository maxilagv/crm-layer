from crm.business_settings.models import SalesPolicy
from crm.sales.domain import policies
from crm.sales.domain.rules import (
    AGGRESSIVE_PATTERN,
    AVAILABILITY_PATTERN,
    CASE_STUDY_PATTERN,
    CONTRACT_CLOSE_PATTERN,
    GUARANTEE_PATTERN,
    PRICE_OBJECTION_PATTERN,
    PRICE_PATTERN,
    SENSITIVE_DATA_PATTERN,
)
from crm.sales.domain.value_objects import SalesPolicyVerdict


class SalesReplyPolicy:
    @staticmethod
    def evaluate(*, organization_id, reply: str, inbound_text: str = "") -> SalesPolicyVerdict:
        reasons: list[str] = []
        violations: list[str] = []
        policy = SalesPolicy.objects.filter(organization_id=organization_id).first()

        if len(reply or "") > policies.MAX_REPLY_CHARS:
            reasons.append("La respuesta es demasiado larga para WhatsApp.")
            violations.append("reply_too_long")
        if PRICE_PATTERN.search(reply or "") and (policy is None or not policy.can_quote_prices):
            reasons.append("La respuesta menciona precios sin politica comercial autorizada.")
            violations.append("unauthorized_price")
        if GUARANTEE_PATTERN.search(reply or ""):
            reasons.append("La respuesta promete resultados garantizados.")
            violations.append("guaranteed_result")
        if AGGRESSIVE_PATTERN.search(reply or ""):
            reasons.append("La respuesta usa presion comercial agresiva.")
            violations.append("aggressive_language")
        if SENSITIVE_DATA_PATTERN.search(reply or ""):
            reasons.append("La respuesta solicita o incluye datos sensibles innecesarios.")
            violations.append("sensitive_data")
        if CONTRACT_CLOSE_PATTERN.search(reply or ""):
            reasons.append("La respuesta intenta cerrar contrato o pago sin humano.")
            violations.append("contract_or_payment_close")
        if AVAILABILITY_PATTERN.search(reply or ""):
            reasons.append("La respuesta menciona disponibilidad no provista por el sistema.")
            violations.append("unverified_availability")
        if CASE_STUDY_PATTERN.search(reply or ""):
            configured_claims = getattr(policy, "forbidden_claims", []) if policy else []
            if not configured_claims:
                reasons.append("La respuesta menciona caso de exito no configurado.")
                violations.append("unverified_case_study")
        if PRICE_OBJECTION_PATTERN.search(inbound_text or ""):
            lowered_reply = (reply or "").lower()
            if not any(word in lowered_reply for word in ("precio", "costo", "valor", "entiendo")):
                reasons.append("La respuesta ignora una objecion explicita de precio.")
                violations.append("ignored_price_objection")

        return SalesPolicyVerdict(
            allowed=not violations,
            reasons=reasons,
            violations=violations,
            sanitized_reply=reply or "",
        )
