from decimal import Decimal

from django.db import models

from crm.core.models import BaseModel

from .domain.enums import DocumentFormat, DocumentStatus, DocumentType


class BrandKit(BaseModel):
    """Per-organization branding + fiscal data used to render documents."""

    business_name = models.CharField(max_length=255, blank=True)
    legal_name = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=64, blank=True)
    email = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    website = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    logo_media = models.ForeignKey(
        "media.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    primary_color = models.CharField(max_length=9, default="#7C6CFF")
    accent_color = models.CharField(max_length=9, default="#22C55E")
    text_color = models.CharField(max_length=9, default="#16161D")
    currency = models.CharField(max_length=8, default="ARS")
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("21"))
    default_terms = models.TextField(blank=True)
    footer_note = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "documents_brand_kit"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_brand_kit_per_org",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
        ]

    def __str__(self) -> str:
        return f"BrandKit({self.business_name or self.organization_id})"


class GeneratedDocument(BaseModel):
    doc_type = models.CharField(max_length=32, choices=DocumentType.choices)
    doc_format = models.CharField(max_length=8, choices=DocumentFormat.choices)
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16, choices=DocumentStatus.choices, default=DocumentStatus.READY
    )
    payload = models.JSONField(default=dict, blank=True)
    media_asset = models.ForeignKey(
        "media.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    client_id = models.UUIDField(null=True, blank=True)
    lead_id = models.UUIDField(null=True, blank=True)
    conversation_id = models.UUIDField(null=True, blank=True)
    contact_id = models.UUIDField(null=True, blank=True)
    ai_run_id = models.UUIDField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "documents_generated_document"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "doc_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.doc_type}:{self.title}"
