from crm.support.models import SupportTicketEvent


def timeline_for_ticket(ticket):
    return SupportTicketEvent.objects.filter(ticket=ticket).order_by("created_at")
