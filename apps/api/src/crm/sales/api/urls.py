from django.urls import path

from .views import (
    SalesCallRequestMarkScheduledView,
    SalesCallRequestsView,
    SalesOpportunitiesView,
)

urlpatterns = [
    path("opportunities/", SalesOpportunitiesView.as_view(), name="sales-opportunities"),
    path("call-requests/", SalesCallRequestsView.as_view(), name="sales-call-requests"),
    path(
        "call-requests/<uuid:call_request_id>/mark-scheduled/",
        SalesCallRequestMarkScheduledView.as_view(),
        name="sales-call-request-mark-scheduled",
    ),
]
