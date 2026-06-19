from rest_framework import serializers

from crm.documents.domain.enums import DocumentFormat, DocumentType
from crm.documents.models import BrandKit, GeneratedDocument


class BrandKitSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandKit
        fields = [
            "id",
            "business_name",
            "legal_name",
            "tax_id",
            "email",
            "phone",
            "website",
            "address",
            "logo_media_id",
            "primary_color",
            "accent_color",
            "text_color",
            "currency",
            "default_tax_rate",
            "default_terms",
            "footer_note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "logo_media_id", "created_at", "updated_at"]


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedDocument
        fields = [
            "id",
            "doc_type",
            "doc_format",
            "title",
            "status",
            "payload",
            "media_asset_id",
            "client_id",
            "lead_id",
            "conversation_id",
            "contact_id",
            "sent_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DocumentCreateSerializer(serializers.Serializer):
    doc_type = serializers.ChoiceField(choices=DocumentType.choices)
    doc_format = serializers.ChoiceField(choices=DocumentFormat.choices)
    payload = serializers.DictField(required=False, default=dict)
    client_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    lead_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    conversation_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    contact_id = serializers.UUIDField(required=False, allow_null=True, default=None)
