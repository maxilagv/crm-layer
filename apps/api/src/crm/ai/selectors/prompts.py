"""Read-side queries for prompts."""

from django.db.models import Prefetch, QuerySet

from crm.ai.models import AIPrompt, AIPromptVersion


def prompts_for_organization(organization, *, purpose: str | None = None) -> QuerySet[AIPrompt]:
    queryset = (
        AIPrompt.objects.filter(organization_id=organization.id)
        .select_related("active_version")
        .prefetch_related(
            Prefetch("versions", queryset=AIPromptVersion.objects.order_by("-version"))
        )
    )
    if purpose:
        queryset = queryset.filter(purpose=purpose)
    return queryset.order_by("key")


def prompt_for_organization(organization, prompt_id) -> AIPrompt | None:
    return (
        AIPrompt.objects.filter(organization_id=organization.id, id=prompt_id)
        .select_related("active_version")
        .first()
    )
