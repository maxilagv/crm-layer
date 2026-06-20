"""Thin media views: assets, signed download URL, internal download, transcription."""

from django.http import FileResponse, Http404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.media.domain.enums import MediaStatus
from crm.media.domain.policies import signed_url_ttl_seconds
from crm.media.selectors.media_assets import (
    media_asset_for_organization,
    media_assets_for_organization,
)
from crm.media.services.media_asset_creator import MediaAssetCreator
from crm.media.services.media_storage import MediaStorageService
from crm.media.storage.signed_urls import SignedURLError, unsign_asset
from crm.organizations.selectors.organizations import resolve_current_organization

from .filters import asset_filters
from .permissions import MediaAssetsPermission, MediaReadPermission
from .serializers import (
    MediaAssetSerializer,
    MediaAssetUploadSerializer,
    SignedURLSerializer,
    TranscriptionRequestSerializer,
    TranscriptionSerializer,
)


def _get_asset_or_404(organization, asset_id):
    asset = media_asset_for_organization(organization, asset_id)
    if asset is None:
        raise NotFound("Media asset not found in current organization")
    return asset


class MediaAssetsView(APIView):
    permission_classes = [MediaAssetsPermission]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(responses=MediaAssetSerializer(many=True))
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = media_assets_for_organization(
            organization, **asset_filters(request.query_params)
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(MediaAssetSerializer(page, many=True).data)

    @extend_schema(request=MediaAssetUploadSerializer, responses=MediaAssetSerializer)
    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = MediaAssetUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        content = upload.read()
        asset = MediaAssetCreator.create_from_bytes(
            organization_id=organization.id,
            content=content,
            file_name=upload.name,
            mime_type=upload.content_type or "application/octet-stream",
            source=serializer.validated_data["source"],
            owner_type=serializer.validated_data["owner_type"],
            owner_id=serializer.validated_data["owner_id"],
            actor=request.user,
            request=request,
        )
        return success_response(request, MediaAssetSerializer(asset).data, status=201)


class MediaAssetDetailView(APIView):
    permission_classes = [MediaReadPermission]

    @extend_schema(responses=MediaAssetSerializer)
    def get(self, request, asset_id):
        organization = resolve_current_organization(request)
        asset = _get_asset_or_404(organization, asset_id)
        return success_response(request, MediaAssetSerializer(asset).data)


class MediaAssetDownloadURLView(APIView):
    permission_classes = [MediaReadPermission]

    @extend_schema(responses=SignedURLSerializer)
    def get(self, request, asset_id):
        organization = resolve_current_organization(request)
        asset = _get_asset_or_404(organization, asset_id)
        signed = MediaStorageService.signed_url(asset, actor=request.user, request=request)
        return success_response(
            request,
            {
                "url": signed.url,
                "expires_in": signed.expires_in,
                "file_name": asset.file_name,
                "mime_type": asset.mime_type,
            },
        )


class MediaInternalDownloadView(APIView):
    """Token-protected streaming endpoint for LocalPrivateStorage signed URLs.

    The token (TimestampSigner) authorizes a single asset for a limited time; the
    storage_key never appears in the URL.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
    def get(self, request):
        from crm.media.models import MediaAsset

        token = request.query_params.get("token", "")
        try:
            asset_id = unsign_asset(token, max_age=signed_url_ttl_seconds())
        except SignedURLError as exc:
            raise NotFound(str(exc)) from exc
        asset = MediaAsset.objects.filter(id=asset_id).first()
        if asset is None or not asset.is_downloadable:
            raise Http404("Asset not available")
        content = MediaStorageService.open_asset(asset)
        response = FileResponse(
            iter([content]), content_type=asset.mime_type or "application/octet-stream"
        )
        response["Content-Disposition"] = f'attachment; filename="{asset.file_name}"'
        return response


class MediaTranscriptionsView(APIView):
    permission_classes = [MediaReadPermission]

    @extend_schema(request=TranscriptionRequestSerializer, responses=TranscriptionSerializer)
    def post(self, request):
        from crm.media.services.audio_transcription import AudioTranscriptionService

        organization = resolve_current_organization(request)
        serializer = TranscriptionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset = _get_asset_or_404(organization, serializer.validated_data["media_asset_id"])
        if asset.status not in (MediaStatus.STORED, MediaStatus.PROCESSED):
            raise ValidationError("Asset is not ready for transcription")
        transcription = AudioTranscriptionService.transcribe(
            media_asset=asset, force=serializer.validated_data["force"], actor=request.user
        )
        return success_response(request, TranscriptionSerializer(transcription).data, status=201)
