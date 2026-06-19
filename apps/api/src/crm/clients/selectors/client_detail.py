from django.db.models import Prefetch

from crm.clients.models import Client, ClientContact, ClientService


def client_detail_for_organization(organization, client_id) -> Client | None:
    return (
        Client.objects.filter(organization_id=organization.id, id=client_id)
        .select_related("contact", "company")
        .prefetch_related(
            Prefetch("client_contacts", queryset=ClientContact.objects.select_related("contact")),
            Prefetch("services", queryset=ClientService.objects.order_by("-created_at")),
        )
        .first()
    )
