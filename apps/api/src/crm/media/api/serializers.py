"""Media serializers. ``storage_key`` is NEVER serialized."""

from rest_framework import serializers

from crm.media.domain.enums import AspectRatio, ImageType, MediaSource
from crm.media.models import GeneratedImage, ImageGenerationRequest, MediaAsset, Transcription


class MediaAssetSerializer(serializers.ModelSerializer):
    is_downloadable = serializers.BooleanField(read_only=True)

    class Meta:
        model = MediaAsset
        # storage_key deliberately excluded: it is never exposed.
        fields = [
            "id",
            "owner_type",
            "owner_id",
            "file_name",
            "mime_type",
            "size_bytes",
            "storage_provider",
            "checksum",
            "source",
            "status",
            "is_downloadable",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class MediaAssetUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    source = serializers.ChoiceField(
        choices=[c for c in MediaSource.choices if c[0] != MediaSource.AI_GENERATED],
        default=MediaSource.DASHBOARD,
    )
    owner_type = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    owner_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class SignedURLSerializer(serializers.Serializer):
    url = serializers.CharField()
    expires_in = serializers.IntegerField()
    file_name = serializers.CharField()
    mime_type = serializers.CharField()


class TranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcription
        fields = [
            "id",
            "media_asset_id",
            "provider",
            "model",
            "language",
            "text",
            "confidence",
            "duration_seconds",
            "status",
            "error_message",
            "ai_run_id",
            "created_at",
        ]
        read_only_fields = fields


class TranscriptionRequestSerializer(serializers.Serializer):
    media_asset_id = serializers.UUIDField()
    force = serializers.BooleanField(required=False, default=False)


class GeneratedImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedImage
        fields = [
            "id",
            "media_asset_id",
            "provider",
            "model",
            "prompt",
            "width",
            "height",
            "created_at",
        ]
        read_only_fields = fields


class ImageGenerationRequestSerializer(serializers.ModelSerializer):
    generated_images = GeneratedImageSerializer(many=True, read_only=True)

    class Meta:
        model = ImageGenerationRequest
        fields = [
            "id",
            "prompt",
            "final_prompt",
            "image_type",
            "aspect_ratio",
            "provider",
            "model",
            "status",
            "result_media_asset_id",
            "error_message",
            "ai_run_id",
            "generated_images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "final_prompt",
            "provider",
            "model",
            "status",
            "result_media_asset_id",
            "error_message",
            "ai_run_id",
            "generated_images",
            "created_at",
            "updated_at",
        ]


class ImageGenerationCreateSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=4000)
    image_type = serializers.ChoiceField(choices=ImageType.choices)
    aspect_ratio = serializers.ChoiceField(choices=AspectRatio.choices, default=AspectRatio.SQUARE)


class SendImageToContactSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    caption = serializers.CharField(required=False, allow_blank=True, default="")
