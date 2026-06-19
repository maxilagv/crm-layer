"""Read-side queries for eval results."""

from django.db.models import QuerySet

from crm.ai.models import AIEvalResult


def eval_results_for_organization(
    organization, *, suite_name: str | None = None, passed: bool | None = None
) -> QuerySet[AIEvalResult]:
    queryset = AIEvalResult.objects.filter(organization_id=organization.id).select_related(
        "eval_case"
    )
    if suite_name:
        queryset = queryset.filter(eval_case__suite_name=suite_name)
    if passed is not None:
        queryset = queryset.filter(passed=passed)
    return queryset.order_by("-created_at")
