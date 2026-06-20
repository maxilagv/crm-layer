from django.contrib import admin

from .models import (
    GeneratedImage,
    ImageGenerationRequest,
    MediaAsset,
    MediaProcessingJob,
    Transcription,
)


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("file_name", "mime_type", "source", "status", "size_bytes", "created_at")
    list_filter = ("source", "status", "storage_provider")
    search_fields = ("file_name", "checksum", "id")
    date_hierarchy = "created_at"
    # storage_key/checksum are sensitive internal data: read-only, never editable.
    readonly_fields = ("id", "storage_key", "checksum", "created_at", "updated_at")


@admin.register(Transcription)
class TranscriptionAdmin(admin.ModelAdmin):
    list_display = ("media_asset", "status", "provider", "model", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("media_asset__id",)
    date_hierarchy = "created_at"
    readonly_fields = tuple(f.name for f in Transcription._meta.fields)

    def has_add_permission(self, request):
        return False


@admin.register(MediaProcessingJob)
class MediaProcessingJobAdmin(admin.ModelAdmin):
    list_display = ("job_type", "status", "media_asset", "attempts", "created_at")
    list_filter = ("job_type", "status")
    date_hierarchy = "created_at"
    readonly_fields = tuple(f.name for f in MediaProcessingJob._meta.fields)

    def has_add_permission(self, request):
        return False


@admin.register(ImageGenerationRequest)
class ImageGenerationRequestAdmin(admin.ModelAdmin):
    list_display = ("image_type", "status", "aspect_ratio", "created_by", "created_at")
    list_filter = ("status", "image_type", "aspect_ratio")
    search_fields = ("prompt", "id")
    date_hierarchy = "created_at"
    readonly_fields = (
        "id",
        "final_prompt",
        "ai_run_id",
        "result_media_asset",
        "created_at",
        "updated_at",
    )


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ("image_generation_request", "media_asset", "provider", "model", "created_at")
    list_filter = ("provider",)
    date_hierarchy = "created_at"
    readonly_fields = tuple(f.name for f in GeneratedImage._meta.fields)

    def has_add_permission(self, request):
        return False
