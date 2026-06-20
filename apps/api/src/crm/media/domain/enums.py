"""Centralized choices for the media module."""

from django.db import models


class MediaSource(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    DASHBOARD = "dashboard", "Dashboard"
    AI_GENERATED = "ai_generated", "AI generated"
    SYSTEM = "system", "System"


class MediaStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    STORED = "stored", "Stored"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"
    DELETED = "deleted", "Deleted"


class StorageProvider(models.TextChoices):
    LOCAL = "local", "Local private"
    S3 = "s3", "S3 compatible"


class TranscriptionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class ProcessingJobType(models.TextChoices):
    DOWNLOAD = "download", "Download"
    VALIDATE = "validate", "Validate"
    TRANSCRIBE = "transcribe", "Transcribe"
    EXTRACT_TICKET = "extract_ticket", "Extract ticket"
    GENERATE_IMAGE = "generate_image", "Generate image"
    STORE_GENERATED_IMAGE = "store_generated_image", "Store generated image"
    CLEANUP = "cleanup", "Cleanup"


class ProcessingJobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    RETRYING = "retrying", "Retrying"
    CANCELLED = "cancelled", "Cancelled"


class ImageType(models.TextChoices):
    PROPOSAL_COVER = "proposal_cover", "Proposal cover"
    INSTAGRAM_POST = "instagram_post", "Instagram post"
    INSTAGRAM_STORY = "instagram_story", "Instagram story"
    BANNER = "banner", "Banner"
    THUMBNAIL = "thumbnail", "Thumbnail"
    AD_CREATIVE = "ad_creative", "Ad creative"
    CLIENT_MOCKUP = "client_mockup", "Client mockup"


class AspectRatio(models.TextChoices):
    SQUARE = "1:1", "1:1"
    PORTRAIT_4_5 = "4:5", "4:5"
    STORY = "9:16", "9:16"
    LANDSCAPE = "16:9", "16:9"
    CLASSIC = "3:2", "3:2"


class ImageGenerationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


# Media kinds (derived from MIME) used by validation/policies.
MEDIA_KIND_AUDIO = "audio"
MEDIA_KIND_IMAGE = "image"
MEDIA_KIND_DOCUMENT = "document"
