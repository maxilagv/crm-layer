"""MediaAssetCreator: validate -> store privately -> persist MediaAsset + events.

The single entry point that turns raw bytes into a private, validated, audited
MediaAsset. Used by uploads, the WhatsApp downloader and generated images.
"""

from django.db import transaction

from crm.audit.services import audit_event_create
from crm.core.services.outbox import create_outbox_event
from crm.media.domain import events
from crm.media.domain.enums import MediaStatus
from crm.media.models import MediaAsset

from ._support import org_stub
from .media_storage import MediaStorageService
from .media_validator import MediaValidator


class MediaAssetCreator:
    @staticmethod
    @transaction.atomic
    def create_from_bytes(
        *,
        organization_id,
        content: bytes,
        file_name: str,
        mime_type: str,
        source: str,
        owner_type: str = "",
        owner_id=None,
        require_known_mime: bool = True,
        actor=None,
        request=None,
        extra_metadata: dict | None = None,
    ) -> MediaAsset:
        validated = MediaValidator.validate(
            content=content,
            mime_type=mime_type,
            file_name=file_name,
            require_known_mime=require_known_mime,
        )
        stored = MediaStorageService.store_bytes(
            organization_id=organization_id,
            content=content,
            file_name=file_name,
            content_type=validated.mime_type,
        )
        asset = MediaAsset.objects.create(
            organization_id=organization_id,
            owner_type=owner_type,
            owner_id=owner_id,
            file_name=file_name,
            mime_type=validated.mime_type,
            size_bytes=validated.size_bytes,
            storage_key=stored.storage_key,
            storage_provider=stored.storage_provider,
            checksum=validated.checksum,
            source=source,
            status=MediaStatus.STORED,
            created_by_id=getattr(actor, "id", None),
            metadata=extra_metadata or {},
        )
        for event_type in (events.ASSET_CREATED, events.ASSET_STORED):
            create_outbox_event(
                event_type=event_type,
                organization_id=organization_id,
                payload={
                    "event_type": event_type,
                    "organization_id": str(organization_id),
                    "data": {
                        "media_asset_id": str(asset.id),
                        "source": source,
                        "kind": validated.kind,
                    },
                    "metadata": {"request_id": getattr(request, "request_id", None)},
                },
            )
        if actor is not None:
            audit_event_create(
                event_type="media_asset_created",
                actor=actor,
                organization=org_stub(organization_id),
                request=request,
                resource_type="media_media_asset",
                resource_id=str(asset.id),
                metadata={"source": source, "mime_type": validated.mime_type},
            )
        return asset

    @staticmethod
    def mark_failed(
        *,
        organization_id,
        file_name: str,
        source: str,
        error: str,
        owner_type: str = "",
        owner_id=None,
    ) -> MediaAsset:
        asset = MediaAsset.objects.create(
            organization_id=organization_id,
            owner_type=owner_type,
            owner_id=owner_id,
            file_name=file_name,
            mime_type="",
            source=source,
            status=MediaStatus.FAILED,
            metadata={"error": error[:500]},
        )
        create_outbox_event(
            event_type=events.ASSET_FAILED,
            organization_id=organization_id,
            payload={
                "event_type": events.ASSET_FAILED,
                "organization_id": str(organization_id),
                "data": {"media_asset_id": str(asset.id), "error": error[:200]},
                "metadata": {},
            },
        )
        return asset
