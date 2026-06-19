from django.urls import path

from .views import (
    BrandKitView,
    DocumentDetailView,
    DocumentDownloadURLView,
    DocumentSendView,
    DocumentsView,
)

urlpatterns = [
    path("brand-kit/", BrandKitView.as_view(), name="brand-kit"),
    path("", DocumentsView.as_view(), name="documents"),
    path("<uuid:document_id>/", DocumentDetailView.as_view(), name="document-detail"),
    path(
        "<uuid:document_id>/download-url/",
        DocumentDownloadURLView.as_view(),
        name="document-download-url",
    ),
    path("<uuid:document_id>/send/", DocumentSendView.as_view(), name="document-send"),
]
