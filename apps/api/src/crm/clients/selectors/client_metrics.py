from django.db.models import Count

from crm.clients.models import Client


def client_counts_by_status(organization) -> list[dict]:
    return list(
        Client.objects.filter(organization_id=organization.id)
        .values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
