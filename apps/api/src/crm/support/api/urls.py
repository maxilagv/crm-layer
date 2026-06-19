from django.urls import path

from .views import (
    KnownIssueDetailView,
    KnownIssuesView,
    TicketAssignView,
    TicketAttachmentsView,
    TicketCommentsView,
    TicketDetailView,
    TicketReopenView,
    TicketResolveView,
    TicketsView,
)

urlpatterns = [
    path("tickets/", TicketsView.as_view(), name="tickets"),
    path("tickets/<uuid:ticket_id>/", TicketDetailView.as_view(), name="ticket-detail"),
    path("tickets/<uuid:ticket_id>/assign/", TicketAssignView.as_view(), name="ticket-assign"),
    path("tickets/<uuid:ticket_id>/resolve/", TicketResolveView.as_view(), name="ticket-resolve"),
    path("tickets/<uuid:ticket_id>/reopen/", TicketReopenView.as_view(), name="ticket-reopen"),
    path(
        "tickets/<uuid:ticket_id>/comments/", TicketCommentsView.as_view(), name="ticket-comments"
    ),
    path(
        "tickets/<uuid:ticket_id>/attachments/",
        TicketAttachmentsView.as_view(),
        name="ticket-attachments",
    ),
    path("support/known-issues/", KnownIssuesView.as_view(), name="known-issues"),
    path(
        "support/known-issues/<uuid:issue_id>/",
        KnownIssueDetailView.as_view(),
        name="known-issue-detail",
    ),
]
