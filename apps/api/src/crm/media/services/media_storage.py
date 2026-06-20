"""MediaStorageService: low-level store / signed-url / delete over an adapter."""

from crm.audit.services import audit_event_create
from crm.media.domain.exceptions import MediaAssetNotDownloadable
from crm.media.domain.policies import signed_url_ttl_seconds
from crm.media.domain.value_objects import SignedURL, StoredFile
from crm.media.storage import get_storage
from crm.media.storage.base import build_storage_key

from ._support import org_stub


class MediaStorageService:
    @staticmethod
    def store_bytes(
        *, organization_id, content: bytes, file_name: str, content_type: str
    ) -> StoredFile:
        storage = get_storage()
        key = build_storage_key(organization_id=organization_id, file_name=file_name)
        return storage.store_file(content=content, key=key, content_type=content_type)

    @staticmethod
    def open_asset(media_asset) -> bytes:
        return get_storage(media_asset.storage_provider).open_file(media_asset.storage_key)

    @staticmethod
    def signed_url(
        media_asset, *, expires_in: int | None = None, actor=None, request=None
    ) -> SignedURL:
        if not media_asset.is_downloadable:
            raise MediaAssetNotDownloadable()
        ttl = expires_in or signed_url_ttl_seconds()
        signed = get_storage(media_asset.storage_provider).generate_signed_url(
            media_asset.storage_key, expires_in=ttl, asset_id=media_asset.id
        )
        audit_event_create(
            event_type="media_signed_url_generated",
            actor=actor,
            organization=org_stub(media_asset.organization_id),
            request=request,
            resource_type="media_media_asset",
            resource_id=str(media_asset.id),
            metadata={"expires_in": signed.expires_in},
        )
        return signed

    @staticmethod
    def delete_asset_file(media_asset) -> None:
        if media_asset.storage_key:
            get_storage(media_asset.storage_provider).delete_file(media_asset.storage_key)
