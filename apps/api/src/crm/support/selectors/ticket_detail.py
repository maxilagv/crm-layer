from django.db.models import Prefetch

from crm.support.models import (
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketComment,
)


def ticket_detail_for_organization(organization, ticket_id) -> SupportTicket | None:
    return (
        SupportTicket.objects.filter(organization_id=organization.id, id=ticket_id)
        .select_related("contact", "client", "assigned_user")
        .prefetch_related(
            Prefetch("comments", queryset=SupportTicketComment.objects.order_by("created_at")),
            Prefetch(
                "attachments",
                queryset=SupportTicketAttachment.objects.select_related("media_asset"),
            ),
        )
        .first()
    )
