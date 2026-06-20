from django.urls import path

from .views import (
    MediaAssetDetailView,
    MediaAssetDownloadURLView,
    MediaAssetsView,
    MediaInternalDownloadView,
    MediaTranscriptionsView,
)

urlpatterns = [
    path("assets/", MediaAssetsView.as_view(), name="media-assets"),
    path("assets/<uuid:asset_id>/", MediaAssetDetailView.as_view(), name="media-asset-detail"),
    path(
        "assets/<uuid:asset_id>/download-url/",
        MediaAssetDownloadURLView.as_view(),
        name="media-asset-download-url",
    ),
    path("transcriptions/", MediaTranscriptionsView.as_view(), name="media-transcriptions"),
    path("internal/download/", MediaInternalDownloadView.as_view(), name="media-internal-download"),
]
