"""DocumentService: render a payload into a branded file, store it privately."""

import re

from django.utils import timezone

from crm.documents.domain.enums import (
    DOCUMENT_TYPE_LABELS,
    EXT_BY_FORMAT,
    MIME_BY_FORMAT,
    DocumentStatus,
)
from crm.documents.domain.payload import normalize_payload
from crm.documents.models import GeneratedDocument
from crm.documents.renderers import get_renderer
from crm.media.domain.enums import MediaSource
from crm.media.services.media_asset_creator import MediaAssetCreator
from crm.media.services.media_storage import MediaStorageService

from .brand_kit import BrandKitService


def _slug(text: str, fallback: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return (s or fallback)[:40]


class DocumentService:
    @staticmethod
    def generate(
        *,
        organization,
        doc_type: str,
        fmt: str,
        payload: dict,
        actor=None,
        status: str = DocumentStatus.READY.value,
        references: dict | None = None,
        request=None,
    ) -> GeneratedDocument:
        kit = BrandKitService.get_or_create(organization)
        brand = BrandKitService.as_render_dict(kit, logo_bytes=DocumentService._logo_bytes(kit))
        normalized = normalize_payload(payload)

        data = get_renderer(fmt)(brand, doc_type, normalized)

        title = normalized["title"] or DOCUMENT_TYPE_LABELS.get(doc_type, "Documento")
        filename = f"{_slug(doc_type, 'doc')}-{_slug(title, 'documento')}.{EXT_BY_FORMAT[fmt]}"
        asset = MediaAssetCreator.create_from_bytes(
            organization_id=organization.id,
            content=data,
            file_name=filename,
            mime_type=MIME_BY_FORMAT[fmt],
            source=MediaSource.SYSTEM,
            owner_type="generated_document",
            actor=actor,
            request=request,
            extra_metadata={"doc_type": doc_type, "format": fmt},
        )

        refs = references or {}
        doc = GeneratedDocument.objects.create(
            organization_id=organization.id,
            doc_type=doc_type,
            doc_format=fmt,
            title=title[:255],
            status=status,
            payload=payload or {},
            media_asset=asset,
            created_by_id=getattr(actor, "id", None),
            client_id=refs.get("client_id"),
            lead_id=refs.get("lead_id"),
            conversation_id=refs.get("conversation_id"),
            contact_id=refs.get("contact_id"),
            ai_run_id=refs.get("ai_run_id"),
        )
        if asset.owner_id is None:
            asset.owner_id = doc.id
            asset.save(update_fields=["owner_id", "updated_at"])
        return doc

    @staticmethod
    def _logo_bytes(kit) -> bytes | None:
        if kit.logo_media_id is None:
            return None
        try:
            return MediaStorageService.open_asset(kit.logo_media)
        except Exception:  # noqa: BLE001 — a missing/broken logo never breaks generation
            return None

    @staticmethod
    def signed_url(doc: GeneratedDocument, *, actor=None, request=None):
        if doc.media_asset_id is None:
            return None
        return MediaStorageService.signed_url(doc.media_asset, actor=actor, request=request)

    @staticmethod
    def mark_sent(doc: GeneratedDocument) -> GeneratedDocument:
        doc.status = DocumentStatus.SENT.value
        doc.sent_at = timezone.now()
        doc.save(update_fields=["status", "sent_at", "updated_at"])
        return doc
