import pytest

from crm.ai.models import AIEvalResult
from crm.ai.services.eval_runner import SUITES, EvalRunner
from tests.factories.organizations import OrganizationFactory


@pytest.mark.django_db
def test_phase9_eval_dataset_loads_and_persists_results() -> None:
    organization = OrganizationFactory()

    report = EvalRunner.run_suite(
        organization_id=organization.id,
        suite_name="support_audio_transcripts",
    )

    assert "support_audio_transcripts" in SUITES
    assert report["total"] >= 1
    assert AIEvalResult.objects.filter(organization_id=organization.id).count() == report["total"]


@pytest.mark.django_db
def test_eval_runner_uses_fake_provider_by_default() -> None:
    organization = OrganizationFactory()

    EvalRunner.run_suite(organization_id=organization.id, suite_name="handoff_cases")

    assert set(
        AIEvalResult.objects.filter(organization_id=organization.id).values_list(
            "provider", flat=True
        )
    ) == {"fake"}
