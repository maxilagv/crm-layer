from django.db.models import QuerySet

from crm.support.models import SupportKnownIssue


def known_issues_for_organization(
    organization, *, status: str | None = None, category: str | None = None
) -> QuerySet[SupportKnownIssue]:
    queryset = SupportKnownIssue.objects.filter(organization_id=organization.id)
    if status:
        queryset = queryset.filter(status=status)
    if category:
        queryset = queryset.filter(category=category)
    return queryset.order_by("-created_at")


def known_issue_for_organization(organization, issue_id) -> SupportKnownIssue | None:
    return SupportKnownIssue.objects.filter(organization_id=organization.id, id=issue_id).first()
