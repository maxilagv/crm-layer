"""Read-side queries for media assets (tenant-scoped)."""

from django.db.models import QuerySet

from crm.media.models import MediaAsset


def media_assets_for_organization(
    organization,
    *,
    source: str | None = None,
    status: str | None = None,
    mime_type: str | None = None,
    owner_type: str | None = None,
    owner_id=None,
) -> QuerySet[MediaAsset]:
    queryset = MediaAsset.objects.filter(organization_id=organization.id)
    if source:
        queryset = queryset.filter(source=source)
    if status:
        queryset = queryset.filter(status=status)
    if mime_type:
        queryset = queryset.filter(mime_type=mime_type)
    if owner_type:
        queryset = queryset.filter(owner_type=owner_type)
    if owner_id:
        queryset = queryset.filter(owner_id=owner_id)
    return queryset.order_by("-created_at")


def media_asset_for_organization(organization, asset_id) -> MediaAsset | None:
    return MediaAsset.objects.filter(organization_id=organization.id, id=asset_id).first()
