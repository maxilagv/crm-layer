"""Image generation endpoints. Generation runs on a worker, never inline."""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.media.selectors.image_generations import (
    image_generation_for_organization,
    image_generations_for_organization,
)
from crm.organizations.selectors.organizations import resolve_current_organization

from .filters import image_generation_filters
from .permissions import MediaReadPermission, MediaWritePermission
from .serializers import (
    ImageGenerationCreateSerializer,
    ImageGenerationRequestSerializer,
    SendImageToContactSerializer,
)


def _get_request_or_404(organization, request_id):
    obj = image_generation_for_organization(organization, request_id)
    if obj is None:
        raise NotFound("Image generation request not found in current organization")
    return obj


class ImageGenerationsView(APIView):
    permission_classes = [MediaReadPermission]

    @extend_schema(responses=ImageGenerationRequestSerializer(many=True))
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = image_generations_for_organization(
            organization, **image_generation_filters(request.query_params)
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(
            ImageGenerationRequestSerializer(page, many=True).data
        )

    @extend_schema(
        request=ImageGenerationCreateSerializer, responses=ImageGenerationRequestSerializer
    )
    def post(self, request):
        from crm.media.services.image_generation import ImageGenerationService

        organization = resolve_current_organization(request)
        serializer = ImageGenerationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image_request = ImageGenerationService.request_generation(
            organization_id=organization.id,
            prompt=serializer.validated_data["prompt"],
            image_type=serializer.validated_data["image_type"],
            aspect_ratio=serializer.validated_data["aspect_ratio"],
            actor=request.user,
            request=request,
        )
        return success_response(
            request, ImageGenerationRequestSerializer(image_request).data, status=202
        )


class ImageGenerationDetailView(APIView):
    permission_classes = [MediaReadPermission]

    @extend_schema(responses=ImageGenerationRequestSerializer)
    def get(self, request, request_id):
        organization = resolve_current_organization(request)
        image_request = _get_request_or_404(organization, request_id)
        return success_response(request, ImageGenerationRequestSerializer(image_request).data)


class ImageGenerationSendToContactView(APIView):
    permission_classes = [MediaWritePermission]

    @extend_schema(request=SendImageToContactSerializer, responses=None)
    def post(self, request, request_id):
        from crm.media.services.image_generation import ImageGenerationService

        organization = resolve_current_organization(request)
        image_request = _get_request_or_404(organization, request_id)
        serializer = SendImageToContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if image_request.result_media_asset_id is None:
            raise ValidationError("Image is not generated yet")
        result = ImageGenerationService.send_to_contact(
            image_request=image_request,
            conversation_id=serializer.validated_data["conversation_id"],
            caption=serializer.validated_data["caption"],
            actor=request.user,
            request=request,
        )
        return success_response(request, result, status=202)
