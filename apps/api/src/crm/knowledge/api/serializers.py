import hashlib

from rest_framework import serializers

from crm.knowledge.models import KnowledgeDocument, KnowledgeSource


class KnowledgeSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeSource
        fields = ["id", "name", "source_type", "status", "metadata", "created_at", "updated_at"]
        read_only_fields = fields


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    source_type = serializers.CharField(source="source.source_type", read_only=True)

    class Meta:
        model = KnowledgeDocument
        fields = [
            "id",
            "source",
            "source_name",
            "source_type",
            "title",
            "content_hash",
            "ingest_status",
            "error_message",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class KnowledgeDocumentCreateSerializer(serializers.Serializer):
    source_id = serializers.UUIDField(required=False)
    source_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    title = serializers.CharField(max_length=255)
    text = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField(required=False)

    def validate(self, attrs):
        if not attrs.get("text") and not attrs.get("file"):
            raise serializers.ValidationError("text or file is required")
        if attrs.get("source_id") and attrs.get("source_name"):
            raise serializers.ValidationError("Use source_id or source_name, not both")
        return attrs


def hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
