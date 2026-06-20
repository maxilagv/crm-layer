from django.urls import path

from .image_views import (
    ImageGenerationDetailView,
    ImageGenerationSendToContactView,
    ImageGenerationsView,
)

urlpatterns = [
    path("", ImageGenerationsView.as_view(), name="image-generations"),
    path("<uuid:request_id>/", ImageGenerationDetailView.as_view(), name="image-generation-detail"),
    path(
        "<uuid:request_id>/send-to-contact/",
        ImageGenerationSendToContactView.as_view(),
        name="image-generation-send-to-contact",
    ),
]
