"""SafetyGuard deterministic rules tests."""

import pytest

from crm.ai.domain.enums import RiskLevel, SafetyDecision
from crm.ai.services.risk_classifier import RiskClassifier
from crm.ai.services.safety_guard import SafetyGuard
from crm.business_settings.models import SalesPolicy
from tests.factories.organizations import OrganizationFactory


@pytest.mark.django_db
def test_safety_guard_allows_safe_sales_reply() -> None:
    organization = OrganizationFactory()
    result = SafetyGuard.evaluate_reply(
        organization_id=organization.id,
        proposed_reply="¡Gracias por escribirnos! ¿Coordinamos una llamada?",
        inbound_text="Hola, quiero info",
    )
    assert result.decision == SafetyDecision.SEND.value
    assert result.risk_level == RiskLevel.LOW.value
    assert result.allows_send


@pytest.mark.django_db
def test_safety_guard_blocks_password_request() -> None:
    organization = OrganizationFactory()
    result = SafetyGuard.evaluate_reply(
        organization_id=organization.id,
        proposed_reply="Pasame tu contraseña y lo reviso",
    )
    assert result.decision == SafetyDecision.DO_NOT_REPLY.value
    assert result.risk_level == RiskLevel.CRITICAL.value
    assert "password_request" in result.policy_violations
    assert result.blocked_phrases


@pytest.mark.django_db
def test_safety_guard_blocks_guaranteed_promise() -> None:
    organization = OrganizationFactory()
    result = SafetyGuard.evaluate_reply(
        organization_id=organization.id,
        proposed_reply="Te garantizamos resultados en 7 días",
    )
    assert result.decision == SafetyDecision.DO_NOT_REPLY.value
    assert "false_promise" in result.policy_violations


@pytest.mark.django_db
def test_safety_guard_blocks_forbidden_price_claim() -> None:
    organization = OrganizationFactory()  # no SalesPolicy -> cannot quote prices
    result = SafetyGuard.evaluate_reply(
        organization_id=organization.id,
        proposed_reply="El plan sale $150.000 por mes",
    )
    assert result.decision == SafetyDecision.REVISE.value
    assert "unauthorized_price" in result.policy_violations


@pytest.mark.django_db
def test_safety_guard_allows_price_when_policy_authorizes() -> None:
    organization = OrganizationFactory()
    SalesPolicy.objects.create(
        organization_id=organization.id, can_quote_prices=True, price_min=100, price_max=500
    )
    result = SafetyGuard.evaluate_reply(
        organization_id=organization.id,
        proposed_reply="El plan básico sale $300 finales",
    )
    assert result.decision == SafetyDecision.SEND.value


@pytest.mark.django_db
def test_safety_guard_handoffs_legal_threat() -> None:
    organization = OrganizationFactory()
    result = SafetyGuard.evaluate_reply(
        organization_id=organization.id,
        proposed_reply="Entiendo tu molestia, lo revisamos",
        inbound_text="Voy a iniciar una demanda con mi abogado",
    )
    assert result.decision == SafetyDecision.HANDOFF_TO_HUMAN.value
    assert result.requires_handoff
    assert result.risk_level == RiskLevel.CRITICAL.value


@pytest.mark.django_db
def test_safety_guard_handoffs_angry_client() -> None:
    organization = OrganizationFactory()
    result = SafetyGuard.evaluate_reply(
        organization_id=organization.id,
        proposed_reply="Lamento la experiencia",
        inbound_text="Es una vergüenza, pésimo servicio, estoy harto",
    )
    assert result.decision == SafetyDecision.HANDOFF_TO_HUMAN.value


@pytest.mark.django_db
def test_safety_guard_critical_failure_notifies_owner() -> None:
    organization = OrganizationFactory()
    result = SafetyGuard.evaluate_reply(
        organization_id=organization.id,
        proposed_reply="Lo estamos revisando",
        inbound_text="URGENTE: produccion caida, no podemos operar",
    )
    assert result.decision == SafetyDecision.HANDOFF_TO_HUMAN.value
    assert result.owner_notification_required


@pytest.mark.django_db
def test_safety_guard_flags_sensitive_data_in_reply() -> None:
    organization = OrganizationFactory()
    result = SafetyGuard.evaluate_reply(
        organization_id=organization.id,
        proposed_reply="La tarjeta es 4111 1111 1111 1111",
    )
    assert result.decision == SafetyDecision.REVISE.value
    assert "sensitive_data_in_reply" in result.policy_violations


@pytest.mark.django_db
def test_safety_guard_honors_model_handoff_request() -> None:
    organization = OrganizationFactory()
    result = SafetyGuard.evaluate_reply(
        organization_id=organization.id,
        proposed_reply="Te derivo con el equipo",
        model_requests_handoff=True,
    )
    assert result.decision == SafetyDecision.HANDOFF_TO_HUMAN.value


def test_risk_classifier_asks_clarification_for_ambiguous_risky_message() -> None:
    result = RiskClassifier.classify_inbound("No entiendo, ¿cómo sería el pago?")
    assert result.decision == SafetyDecision.ASK_CLARIFYING_QUESTION.value


def test_risk_classifier_low_risk_passthrough() -> None:
    result = RiskClassifier.classify_inbound("Gracias, nos vemos mañana")
    assert result.decision == SafetyDecision.SEND.value
    assert result.risk_level == RiskLevel.LOW.value
