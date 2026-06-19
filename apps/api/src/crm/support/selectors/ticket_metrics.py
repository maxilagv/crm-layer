from django.db.models import Count

from crm.support.models import SupportTicket


def ticket_counts_by_status(organization) -> list[dict]:
    return list(
        SupportTicket.objects.filter(organization_id=organization.id)
        .values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
