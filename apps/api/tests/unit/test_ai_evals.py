"""Eval runner tests: suites run deterministically and persist results."""

import pytest

from crm.ai.models import AIEvalCase, AIEvalResult
from crm.ai.services.eval_runner import SUITES, EvalRunner
from tests.factories.organizations import OrganizationFactory


@pytest.mark.django_db
def test_eval_suite_runs_and_persists_results() -> None:
    organization = OrganizationFactory()
    report = EvalRunner.run_suite(organization_id=organization.id, suite_name="sales_agent")
    assert report["total"] >= 6
    assert report["passed"] == report["total"]
    assert report["schema_validity_rate"] is not None
    assert AIEvalResult.objects.filter(organization_id=organization.id).count() == report["total"]


@pytest.mark.django_db
def test_sales_eval_detects_bad_price_claim() -> None:
    organization = OrganizationFactory()
    EvalRunner.run_suite(organization_id=organization.id, suite_name="sales_agent")
    result = AIEvalResult.objects.get(
        organization_id=organization.id, eval_case__case_key="precio_sin_politica"
    )
    assert result.passed  # expected_behavior "revise" matched
    assert result.metrics["safety_decision"] == "revise"


@pytest.mark.django_db
def test_risk_eval_detects_handoff_case() -> None:
    organization = OrganizationFactory()
    EvalRunner.run_suite(organization_id=organization.id, suite_name="risk_classifier")
    result = AIEvalResult.objects.get(
        organization_id=organization.id, eval_case__case_key="ignora_amenaza_legal"
    )
    assert result.passed
    assert result.metrics["safety_decision"] == "handoff_to_human"


@pytest.mark.django_db
def test_task_extraction_eval_counts_tasks() -> None:
    organization = OrganizationFactory()
    EvalRunner.run_suite(organization_id=organization.id, suite_name="task_extraction")
    result = AIEvalResult.objects.get(
        organization_id=organization.id, eval_case__case_key="sin_tareas"
    )
    assert result.passed
    assert result.metrics["tasks_count"] == 0


@pytest.mark.django_db
def test_eval_seed_is_idempotent_and_run_all_covers_every_suite() -> None:
    organization = OrganizationFactory()
    reports = EvalRunner.run_all(organization_id=organization.id)
    assert {report["suite"] for report in reports} == set(SUITES)
    case_count = AIEvalCase.objects.filter(organization_id=organization.id).count()
    EvalRunner.run_all(organization_id=organization.id)  # re-run: no duplicate cases
    assert AIEvalCase.objects.filter(organization_id=organization.id).count() == case_count
