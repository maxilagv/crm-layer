"""Media storage, signed URLs and validation tests."""

import pytest

from crm.media.domain.enums import MediaSource, MediaStatus
from crm.media.domain.exceptions import (
    EmptyMediaFile,
    MediaTooLarge,
    UnsupportedMediaType,
)
from crm.media.domain.rules import is_safe_storage_key
from crm.media.services.media_asset_creator import MediaAssetCreator
from crm.media.services.media_storage import MediaStorageService
from crm.media.storage import LocalPrivateStorage
from crm.media.storage.validators import validate_media
from tests.factories.organizations import OrganizationFactory

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture(autouse=True)
def _private_media(settings, tmp_path):
    settings.MEDIA_PRIVATE_ROOT = str(tmp_path / "private_media")


@pytest.mark.django_db
def test_media_asset_private_storage():
    org = OrganizationFactory()
    asset = MediaAssetCreator.create_from_bytes(
        organization_id=org.id,
        content=PNG,
        file_name="captura.png",
        mime_type="image/png",
        source=MediaSource.DASHBOARD,
    )
    assert asset.status == MediaStatus.STORED
    assert asset.storage_provider == "local"
    # storage_key is tenant-prefixed and traversal-safe.
    assert asset.storage_key.startswith(f"{org.id}/")
    assert is_safe_storage_key(asset.storage_key)
    # The bytes are retrievable from private storage and round-trip intact.
    assert MediaStorageService.open_asset(asset) == PNG
    assert asset.checksum and asset.size_bytes == len(PNG)


@pytest.mark.django_db
def test_media_asset_generates_checksum_and_size():
    org = OrganizationFactory()
    import hashlib

    asset = MediaAssetCreator.create_from_bytes(
        organization_id=org.id,
        content=PNG,
        file_name="x.png",
        mime_type="image/png",
        source=MediaSource.DASHBOARD,
    )
    assert asset.checksum == hashlib.sha256(PNG).hexdigest()


def test_validate_media_rejects_bad_inputs():
    with pytest.raises(EmptyMediaFile):
        validate_media(content=b"", mime_type="image/png", file_name="a.png")
    with pytest.raises(UnsupportedMediaType):
        validate_media(content=b"x", mime_type="application/x-msdownload", file_name="a.exe")
    with pytest.raises(UnsupportedMediaType):
        # Dangerous extension rejected regardless of MIME.
        validate_media(content=b"x", mime_type="image/png", file_name="evil.exe")


def test_validate_media_size_limit(settings):
    settings.MEDIA_MAX_SIZE_BYTES = 10
    with pytest.raises(MediaTooLarge):
        validate_media(content=b"x" * 11, mime_type="image/png", file_name="a.png")


def test_storage_key_rejects_path_traversal():
    assert is_safe_storage_key("org/2026/06/12/uuid_file.png") is True
    assert is_safe_storage_key("../etc/passwd") is False
    assert is_safe_storage_key("/abs/path") is False
    assert is_safe_storage_key("a//b") is False


@pytest.mark.django_db
def test_local_storage_rejects_traversal_key():
    from crm.media.domain.exceptions import UnsafeStorageKey

    storage = LocalPrivateStorage()
    with pytest.raises(UnsafeStorageKey):
        storage.open_file("../../secret")


@pytest.mark.django_db
def test_signed_url_for_local_storage_does_not_expose_storage_key():
    org = OrganizationFactory()
    asset = MediaAssetCreator.create_from_bytes(
        organization_id=org.id,
        content=PNG,
        file_name="x.png",
        mime_type="image/png",
        source=MediaSource.DASHBOARD,
    )
    signed = MediaStorageService.signed_url(asset, expires_in=300)
    assert signed.expires_in == 300
    assert asset.storage_key not in signed.url
    assert "token=" in signed.url


@pytest.mark.django_db
def test_signed_url_requires_downloadable_asset():
    from crm.media.domain.exceptions import MediaAssetNotDownloadable

    org = OrganizationFactory()
    asset = MediaAssetCreator.mark_failed(
        organization_id=org.id, file_name="x", source=MediaSource.WHATSAPP, error="boom"
    )
    with pytest.raises(MediaAssetNotDownloadable):
        MediaStorageService.signed_url(asset)
