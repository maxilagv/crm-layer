"""S3/R2/MinIO-compatible private storage using presigned URLs.

boto3 is imported lazily so the dependency is only required in environments that
actually use S3. The bucket must be private; access is granted only through
short-lived presigned GET URLs.
"""

from django.conf import settings

from crm.media.domain.exceptions import MediaError
from crm.media.domain.policies import signed_url_ttl_seconds
from crm.media.domain.value_objects import SignedURL, StoredFile

from .base import BaseStorage, checksum_of


class S3PrivateStorage(BaseStorage):
    provider = "s3"

    def __init__(self, *, client=None, bucket: str | None = None):
        self._client = client
        self.bucket = bucket or getattr(settings, "S3_BUCKET_NAME", "")
        if not self.bucket:
            raise MediaError("S3_BUCKET_NAME is not configured")

    @property
    def client(self):
        if self._client is None:
            import boto3  # lazy import

            self._client = boto3.client(
                "s3",
                endpoint_url=getattr(settings, "S3_ENDPOINT_URL", "") or None,
                aws_access_key_id=getattr(settings, "S3_ACCESS_KEY_ID", "") or None,
                aws_secret_access_key=getattr(settings, "S3_SECRET_ACCESS_KEY", "") or None,
                region_name=getattr(settings, "S3_REGION", "") or None,
            )
        return self._client

    def store_file(self, *, content: bytes, key: str, content_type: str) -> StoredFile:
        self._guard(key)
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=content, ContentType=content_type, ACL="private"
        )
        return StoredFile(
            storage_key=key,
            storage_provider=self.provider,
            size_bytes=len(content),
            checksum=checksum_of(content),
        )

    def open_file(self, storage_key: str) -> bytes:
        self._guard(storage_key)
        response = self.client.get_object(Bucket=self.bucket, Key=storage_key)
        return response["Body"].read()

    def delete_file(self, storage_key: str) -> None:
        self._guard(storage_key)
        self.client.delete_object(Bucket=self.bucket, Key=storage_key)

    def exists(self, storage_key: str) -> bool:
        self._guard(storage_key)
        try:
            self.client.head_object(Bucket=self.bucket, Key=storage_key)
            return True
        except Exception:
            return False

    def generate_signed_url(self, storage_key: str, *, expires_in: int, asset_id=None) -> SignedURL:
        self._guard(storage_key)
        ttl = expires_in or signed_url_ttl_seconds()
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_key},
            ExpiresIn=ttl,
        )
        return SignedURL(url=url, expires_in=ttl)
