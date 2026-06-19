"""Thin document views: brand kit, generate, list, detail, download URL, send."""

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView

from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.documents.models import GeneratedDocument
from crm.documents.services.brand_kit import BrandKitService
from crm.documents.services.document_service import DocumentService
from crm.media.domain.exceptions import MediaAssetNotDownloadable
from crm.organizations.selectors.organizations import resolve_current_organization

from .permissions import (
    BrandKitPermission,
    DocumentReadPermission,
    DocumentsPermission,
    DocumentWritePermission,
)
from .serializers import (
    BrandKitSerializer,
    DocumentCreateSerializer,
    GeneratedDocumentSerializer,
)

_BRAND_FIELDS = (
    "business_name",
    "legal_name",
    "tax_id",
    "email",
    "phone",
    "website",
    "address",
    "primary_color",
    "accent_color",
    "text_color",
    "currency",
    "default_tax_rate",
    "default_terms",
    "footer_note",
)


def _get_document_or_404(organization, document_id) -> GeneratedDocument:
    doc = GeneratedDocument.objects.filter(organization_id=organization.id, id=document_id).first()
    if doc is None:
        raise NotFound("Documento no encontrado en esta organización")
    return doc


class BrandKitView(APIView):
    permission_classes = [BrandKitPermission]

    def get(self, request):
        organization = resolve_current_organization(request)
        kit = BrandKitService.get_or_create(organization)
        return success_response(request, BrandKitSerializer(kit).data)

    def patch(self, request):
        organization = resolve_current_organization(request)
        kit = BrandKitService.get_or_create(organization)
        serializer = BrandKitSerializer(kit, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        dirty = [f for f in _BRAND_FIELDS if f in serializer.validated_data]
        for field in dirty:
            setattr(kit, field, serializer.validated_data[field])
        if dirty:
            kit.updated_by_id = request.user.id
            kit.save(update_fields=[*dirty, "updated_by_id", "updated_at"])
        return success_response(request, BrandKitSerializer(kit).data)


class DocumentsView(APIView):
    permission_classes = [DocumentsPermission]

    def get(self, request):
        organization = resolve_current_organization(request)
        qs = GeneratedDocument.objects.filter(organization_id=organization.id)
        params = request.query_params
        if params.get("doc_type"):
            qs = qs.filter(doc_type=params["doc_type"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("format"):
            qs = qs.filter(doc_format=params["format"])
        if params.get("search"):
            qs = qs.filter(title__icontains=params["search"])
        qs = qs.order_by("-created_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(GeneratedDocumentSerializer(page, many=True).data)

    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = DocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        doc = DocumentService.generate(
            organization=organization,
            doc_type=data["doc_type"],
            fmt=data["doc_format"],
            payload=data["payload"],
            actor=request.user,
            request=request,
            references={
                "client_id": data["client_id"],
                "lead_id": data["lead_id"],
                "conversation_id": data["conversation_id"],
                "contact_id": data["contact_id"],
            },
        )
        body = GeneratedDocumentSerializer(doc).data
        signed = DocumentService.signed_url(doc, actor=request.user, request=request)
        body["download_url"] = signed.url if signed else None
        return success_response(request, body, status=201)


class DocumentDetailView(APIView):
    permission_classes = [DocumentReadPermission]

    def get(self, request, document_id):
        organization = resolve_current_organization(request)
        doc = _get_document_or_404(organization, document_id)
        return success_response(request, GeneratedDocumentSerializer(doc).data)


class DocumentDownloadURLView(APIView):
    permission_classes = [DocumentReadPermission]

    def get(self, request, document_id):
        organization = resolve_current_organization(request)
        doc = _get_document_or_404(organization, document_id)
        try:
            signed = DocumentService.signed_url(doc, actor=request.user, request=request)
        except MediaAssetNotDownloadable as exc:
            raise ValidationError("El documento no está disponible para descarga") from exc
        if signed is None:
            raise ValidationError("El documento no tiene archivo asociado")
        return success_response(
            request,
            {
                "url": signed.url,
                "expires_in": signed.expires_in,
                "file_name": doc.media_asset.file_name,
                "mime_type": doc.media_asset.mime_type,
                "title": doc.title,
            },
        )


class DocumentSendView(APIView):
    permission_classes = [DocumentWritePermission]

    def post(self, request, document_id):
        organization = resolve_current_organization(request)
        doc = _get_document_or_404(organization, document_id)
        DocumentService.mark_sent(doc)
        body = GeneratedDocumentSerializer(doc).data
        signed = DocumentService.signed_url(doc, actor=request.user, request=request)
        body["download_url"] = signed.url if signed else None
        return success_response(request, body)
