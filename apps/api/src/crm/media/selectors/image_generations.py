"""Read-side queries for image generation history."""

from django.db.models import QuerySet

from crm.media.models import ImageGenerationRequest


def image_generations_for_organization(
    organization,
    *,
    status: str | None = None,
    image_type: str | None = None,
    aspect_ratio: str | None = None,
    created_by_id=None,
) -> QuerySet[ImageGenerationRequest]:
    queryset = ImageGenerationRequest.objects.filter(
        organization_id=organization.id
    ).select_related("result_media_asset")
    if status:
        queryset = queryset.filter(status=status)
    if image_type:
        queryset = queryset.filter(image_type=image_type)
    if aspect_ratio:
        queryset = queryset.filter(aspect_ratio=aspect_ratio)
    if created_by_id:
        queryset = queryset.filter(created_by_id=created_by_id)
    return queryset.order_by("-created_at")


def image_generation_for_organization(organization, request_id) -> ImageGenerationRequest | None:
    return (
        ImageGenerationRequest.objects.filter(organization_id=organization.id, id=request_id)
        .select_related("result_media_asset")
        .first()
    )
