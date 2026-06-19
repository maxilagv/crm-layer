from crm.clients.models import ClientContact, ClientService


def contacts_for_client(client):
    return (
        ClientContact.objects.filter(client=client)
        .select_related("contact")
        .order_by("-is_primary", "created_at")
    )


def services_for_client(client):
    return ClientService.objects.filter(client=client).order_by("-created_at")
