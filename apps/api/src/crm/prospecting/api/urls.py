from django.urls import path

from .views import (
    CampaignDetailView,
    CampaignDiscoverView,
    CampaignRunOutreachView,
    CampaignsView,
    ProspectDetailView,
    ProspectsView,
)

urlpatterns = [
    path("campaigns/", CampaignsView.as_view(), name="prospecting-campaigns"),
    path(
        "campaigns/<uuid:campaign_id>/",
        CampaignDetailView.as_view(),
        name="prospecting-campaign-detail",
    ),
    path(
        "campaigns/<uuid:campaign_id>/discover/",
        CampaignDiscoverView.as_view(),
        name="prospecting-campaign-discover",
    ),
    path(
        "campaigns/<uuid:campaign_id>/run-outreach/",
        CampaignRunOutreachView.as_view(),
        name="prospecting-campaign-run-outreach",
    ),
    path("prospects/", ProspectsView.as_view(), name="prospecting-prospects"),
    path(
        "prospects/<uuid:prospect_id>/",
        ProspectDetailView.as_view(),
        name="prospecting-prospect-detail",
    ),
]
