"""Media domain models.

``MediaAsset`` is private by default: ``storage_key`` is an internal path and is
NEVER exposed as a URL — downloads go through short-lived signed URLs. Every
asset carries ``organization_id`` (UUID, BaseModel convention), an owner
(type+id), validated MIME, size and checksum.
"""

from django.conf import settings
from django.db import models

from crm.core.models import BaseModel

from .domain.enums import (
    AspectRatio,
    ImageGenerationStatus,
    ImageType,
    MediaSource,
    MediaStatus,
    ProcessingJobStatus,
    ProcessingJobType,
    StorageProvider,
    TranscriptionStatus,
)


class MediaAsset(BaseModel):
    owner_type = models.CharField(max_length=64)
    owner_id = models.UUIDField(null=True, blank=True)
    file_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=120)
    size_bytes = models.PositiveBigIntegerField(default=0)
    # Internal storage path; never returned to clients as a public URL.
    storage_key = models.CharField(max_length=512, blank=True)
    storage_provider = models.CharField(
        max_length=16, choices=StorageProvider.choices, default=StorageProvider.LOCAL
    )
    checksum = models.CharField(max_length=64, blank=True)
    source = models.CharField(max_length=16, choices=MediaSource.choices)
    status = models.CharField(
        max_length=16, choices=MediaStatus.choices, default=MediaStatus.PENDING
    )

    class Meta:
        db_table = "media_media_asset"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "owner_type", "owner_id"]),
            models.Index(fields=["organization_id", "source"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "mime_type"]),
            models.Index(fields=["checksum"]),
        ]

    @property
    def is_downloadable(self) -> bool:
        return self.status in (MediaStatus.STORED, MediaStatus.PROCESSED) and bool(self.storage_key)

    def __str__(self) -> str:
        return f"{self.file_name} ({self.source})"


class Transcription(BaseModel):
    media_asset = models.ForeignKey(
        MediaAsset, on_delete=models.CASCADE, related_name="transcriptions"
    )
    provider = models.CharField(max_length=32, blank=True)
    model = models.CharField(max_length=120, blank=True)
    language = models.CharField(max_length=16, default="es")
    text = models.TextField(blank=True)
    confidence = models.FloatField(null=True, blank=True)
    duration_seconds = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=16, choices=TranscriptionStatus.choices, default=TranscriptionStatus.PENDING
    )
    error_message = models.TextField(blank=True)
    ai_run_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "media_transcription"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "media_asset"]),
            models.Index(fields=["organization_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"transcription:{self.media_asset_id}:{self.status}"


class MediaProcessingJob(BaseModel):
    media_asset = models.ForeignKey(
        MediaAsset, on_delete=models.CASCADE, related_name="processing_jobs", null=True, blank=True
    )
    job_type = models.CharField(max_length=32, choices=ProcessingJobType.choices)
    status = models.CharField(
        max_length=16, choices=ProcessingJobStatus.choices, default=ProcessingJobStatus.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    available_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "media_processing_job"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "media_asset"]),
            models.Index(fields=["organization_id", "job_type", "status"]),
            models.Index(fields=["available_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.job_type}:{self.status}"


class ImageGenerationRequest(BaseModel):
    prompt = models.TextField()
    final_prompt = models.TextField(blank=True)
    image_type = models.CharField(max_length=32, choices=ImageType.choices)
    aspect_ratio = models.CharField(
        max_length=8, choices=AspectRatio.choices, default=AspectRatio.SQUARE
    )
    provider = models.CharField(max_length=32, blank=True)
    model = models.CharField(max_length=120, blank=True)
    status = models.CharField(
        max_length=16,
        choices=ImageGenerationStatus.choices,
        default=ImageGenerationStatus.PENDING,
    )
    result_media_asset = models.ForeignKey(
        MediaAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="image_generation_requests",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="image_generation_requests",
    )
    error_message = models.TextField(blank=True)
    ai_run_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "media_image_generation_request"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "image_type"]),
            models.Index(fields=["organization_id", "created_by"]),
        ]

    def __str__(self) -> str:
        return f"image_request:{self.image_type}:{self.status}"


class GeneratedImage(BaseModel):
    image_generation_request = models.ForeignKey(
        ImageGenerationRequest, on_delete=models.CASCADE, related_name="generated_images"
    )
    media_asset = models.ForeignKey(
        MediaAsset, on_delete=models.PROTECT, related_name="generated_image_records"
    )
    provider = models.CharField(max_length=32, blank=True)
    model = models.CharField(max_length=120, blank=True)
    prompt = models.TextField(blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "media_generated_image"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "image_generation_request"]),
            models.Index(fields=["organization_id", "media_asset"]),
        ]

    def __str__(self) -> str:
        return f"generated_image:{self.id}"
