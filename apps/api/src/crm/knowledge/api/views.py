from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.documents.api.permissions import DocumentReadPermission, DocumentsPermission
from crm.knowledge.models import KnowledgeDocument, KnowledgeSource, sha256_text
from crm.knowledge.tasks import ingest_document
from crm.media.domain.enums import MediaSource
from crm.media.services.media_asset_creator import MediaAssetCreator
from crm.organizations.selectors.organizations import resolve_current_organization

from .serializers import (
    KnowledgeDocumentCreateSerializer,
    KnowledgeDocumentSerializer,
    KnowledgeSourceSerializer,
    hash_bytes,
)


class KnowledgeSourcesView(APIView):
    permission_classes = [DocumentReadPermission]

    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = KnowledgeSource.objects.filter(organization_id=organization.id).order_by(
            "-created_at"
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(KnowledgeSourceSerializer(page, many=True).data)


class KnowledgeDocumentsView(APIView):
    permission_classes = [DocumentsPermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = (
            KnowledgeDocument.objects.filter(organization_id=organization.id)
            .select_related("source")
            .order_by("-created_at")
        )
        if request.query_params.get("status"):
            queryset = queryset.filter(ingest_status=request.query_params["status"])
        if request.query_params.get("source_id"):
            queryset = queryset.filter(source_id=request.query_params["source_id"])
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(KnowledgeDocumentSerializer(page, many=True).data)

    def post(self, request):
        organization = resolve_current_organization(request)
        serializer = KnowledgeDocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        upload = data.get("file")
        is_pdf = bool(upload)
        source = _resolve_source(
            organization_id=organization.id,
            source_id=data.get("source_id"),
            source_name=data.get("source_name") or ("PDF" if is_pdf else "Manual"),
            source_type=(
                KnowledgeSource.SourceType.PDF if is_pdf else KnowledgeSource.SourceType.MANUAL_TEXT
            ),
        )
        if is_pdf:
            content = upload.read()
            asset = MediaAssetCreator.create_from_bytes(
                organization_id=organization.id,
                content=content,
                file_name=upload.name,
                mime_type=upload.content_type or "application/pdf",
                source=MediaSource.DASHBOARD,
                owner_type="knowledge_document",
                owner_id=None,
                actor=request.user,
                request=request,
            )
            document = _create_pending_document(
                organization_id=organization.id,
                source=source,
                title=data["title"],
                raw_text="",
                content_hash=hash_bytes(content),
                metadata={"media_asset_id": str(asset.id)},
            )
            asset.owner_id = document.id
            asset.save(update_fields=["owner_id", "updated_at"])
        else:
            text = data.get("text", "")
            document = _create_pending_document(
                organization_id=organization.id,
                source=source,
                title=data["title"],
                raw_text=text,
                content_hash=sha256_text(text),
                metadata={},
            )
        ingest_document.delay(document_id=str(document.id))
        document.refresh_from_db()
        return success_response(
            request,
            {
                "document_id": str(document.id),
                "ingest_status": KnowledgeDocument.IngestStatus.PENDING,
            },
            status=202,
        )


def _resolve_source(*, organization_id, source_id, source_name: str, source_type: str):
    if source_id:
        source = KnowledgeSource.objects.filter(
            organization_id=organization_id, id=source_id
        ).first()
        if source is None:
            raise NotFound("Knowledge source not found in current organization")
        return source
    if not source_name:
        raise ValidationError("source_name is required when source_id is not provided")
    source, _ = KnowledgeSource.objects.get_or_create(
        organization_id=organization_id,
        name=source_name,
        source_type=source_type,
        defaults={"status": KnowledgeSource.Status.ACTIVE},
    )
    return source


def _create_pending_document(
    *, organization_id, source, title: str, raw_text: str, content_hash: str, metadata: dict
) -> KnowledgeDocument:
    document, _ = KnowledgeDocument.objects.get_or_create(
        organization_id=organization_id,
        source=source,
        content_hash=content_hash,
        defaults={
            "title": title,
            "raw_text": raw_text,
            "ingest_status": KnowledgeDocument.IngestStatus.PENDING,
            "metadata": metadata,
        },
    )
    return document
