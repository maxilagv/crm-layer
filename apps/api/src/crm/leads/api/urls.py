from django.urls import path

from .views import (
    LeadConvertToClientView,
    LeadDetailView,
    LeadMarkLostView,
    LeadScheduleFollowupView,
    LeadScoreView,
    LeadsView,
)

urlpatterns = [
    path("", LeadsView.as_view(), name="leads-list"),
    path("<uuid:lead_id>/", LeadDetailView.as_view(), name="leads-detail"),
    path("<uuid:lead_id>/score/", LeadScoreView.as_view(), name="leads-score"),
    path(
        "<uuid:lead_id>/convert-to-client/",
        LeadConvertToClientView.as_view(),
        name="leads-convert-to-client",
    ),
    path("<uuid:lead_id>/mark-lost/", LeadMarkLostView.as_view(), name="leads-mark-lost"),
    path(
        "<uuid:lead_id>/schedule-followup/",
        LeadScheduleFollowupView.as_view(),
        name="leads-schedule-followup",
    ),
]
