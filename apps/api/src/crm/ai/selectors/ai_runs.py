"""Read-side queries for AI runs (tenant-scoped)."""

from django.db.models import QuerySet

from crm.ai.models import AIRun


def runs_for_organization(
    organization,
    *,
    purpose: str | None = None,
    status: str | None = None,
    provider: str | None = None,
    conversation_id=None,
) -> QuerySet[AIRun]:
    queryset = AIRun.objects.filter(organization_id=organization.id).select_related(
        "prompt_version__prompt"
    )
    if purpose:
        queryset = queryset.filter(purpose=purpose)
    if status:
        queryset = queryset.filter(status=status)
    if provider:
        queryset = queryset.filter(provider=provider)
    if conversation_id:
        queryset = queryset.filter(conversation_id=conversation_id)
    return queryset.order_by("-created_at")


def run_for_organization(organization, run_id) -> AIRun | None:
    return (
        AIRun.objects.filter(organization_id=organization.id, id=run_id)
        .select_related("prompt_version__prompt")
        .first()
    )
