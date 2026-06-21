"""Models for the autonomous sales agent: campaigns and prospects."""

from django.db import models
from django.utils import timezone

from crm.core.models import BaseModel

from .domain.enums import CampaignSource, CampaignStatus, ProspectChannel, ProspectStatus


class ProspectingCampaign(BaseModel):
    """A hunting campaign: a vertical + a place query + qualification criteria."""

    name = models.CharField(max_length=255)
    vertical = models.CharField(max_length=120, blank=True)  # "gomerías", "talleres"
    query = models.CharField(max_length=255)  # Google Places text query
    location_hint = models.CharField(max_length=255, blank=True)  # "Palermo, CABA"
    status = models.CharField(
        max_length=16, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT
    )
    channel = models.CharField(
        max_length=16, choices=ProspectChannel.choices, default=ProspectChannel.WHATSAPP
    )
    source = models.CharField(
        max_length=32, choices=CampaignSource.choices, default=CampaignSource.GOOGLE_PLACES
    )
    # What "needs digital professionalization" means for this vertical (feeds the qualifier).
    target_profile = models.TextField(blank=True)
    min_fit_score = models.PositiveSmallIntegerField(default=60)
    # If True, prospects above min_fit_score are contacted without manual approval (still capped).
    auto_contact = models.BooleanField(default=False)
    # If False, Cazador drafts and notifies the owner; autonomous sends are opt-in per campaign.
    auto_reply = models.BooleanField(default=False)
    auto_followup = models.BooleanField(default=False)
    max_touches = models.PositiveSmallIntegerField(default=3)
    daily_cap = models.PositiveSmallIntegerField(default=20)
    # Denormalized counters for the dashboard.
    discovered_count = models.PositiveIntegerField(default=0)
    qualified_count = models.PositiveIntegerField(default=0)
    contacted_count = models.PositiveIntegerField(default=0)
    interested_count = models.PositiveIntegerField(default=0)
    last_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "prospecting_campaign"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "source"]),
        ]

    def __str__(self) -> str:
        return self.name


class Prospect(BaseModel):
    """A business discovered for a campaign, with its digital footprint + AI verdict."""

    campaign = models.ForeignKey(
        ProspectingCampaign, on_delete=models.CASCADE, related_name="prospects"
    )
    # Discovery (Google Places).
    place_id = models.CharField(max_length=255, blank=True)  # dedup key
    external_source = models.CharField(max_length=32, blank=True)
    external_id = models.CharField(max_length=255, blank=True)
    business_name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=500, blank=True)
    phone = models.CharField(max_length=64, blank=True)  # E.164 when available
    website = models.CharField(max_length=500, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    reviews_count = models.PositiveIntegerField(default=0)
    photos_count = models.PositiveIntegerField(default=0)
    raw_data = models.JSONField(default=dict, blank=True)
    # Enrichment (the "private investigator": web analysis + review mining + extra Places signals).
    # None = not investigated yet; True/False = investigated.
    website_reachable = models.BooleanField(null=True, blank=True)
    website_platform = models.CharField(max_length=64, blank=True)  # wordpress, wix, tiendanube...
    has_online_booking = models.BooleanField(null=True, blank=True)
    latest_review_age_days = models.PositiveIntegerField(null=True, blank=True)
    # PageSpeed Insights mobile performance score (0-100); low = slow site = strong pitch.
    pagespeed_score = models.PositiveSmallIntegerField(null=True, blank=True)
    owner_name = models.CharField(max_length=255, blank=True)
    owner_email = models.EmailField(blank=True)
    owner_email_score = models.PositiveSmallIntegerField(null=True, blank=True)
    owner_title = models.CharField(max_length=255, blank=True)
    # Catch-all so we don't over-column: https, mobile_friendly, ecommerce, emails, social_links,
    # price_level, editorial_summary, review_themes, lat/lng, etc.
    enrichment = models.JSONField(default=dict, blank=True)
    enriched_at = models.DateTimeField(null=True, blank=True)
    # Lifecycle + AI qualification.
    status = models.CharField(
        max_length=20, choices=ProspectStatus.choices, default=ProspectStatus.DISCOVERED
    )
    fit_score = models.PositiveSmallIntegerField(null=True, blank=True)  # 0-100
    signals = models.JSONField(default=list, blank=True)  # ["no_website", "few_photos"]
    reasoning = models.TextField(blank=True)
    recommended_angle = models.TextField(blank=True)
    # Links into the CRM once we act on the prospect.
    contact_id = models.UUIDField(null=True, blank=True)
    conversation_id = models.UUIDField(null=True, blank=True)
    lead_id = models.UUIDField(null=True, blank=True)
    ai_run_id = models.UUIDField(null=True, blank=True)
    qualified_at = models.DateTimeField(null=True, blank=True)
    contacted_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    touch_count = models.PositiveSmallIntegerField(default=0)
    last_touch_at = models.DateTimeField(null=True, blank=True)
    next_followup_at = models.DateTimeField(null=True, blank=True)
    follow_up_count = models.PositiveSmallIntegerField(default=0)
    error_message = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "prospecting_prospect"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "campaign", "place_id"],
                condition=models.Q(deleted_at__isnull=True) & ~models.Q(place_id=""),
                name="uniq_prospect_campaign_place",
            ),
            models.UniqueConstraint(
                fields=["organization_id", "campaign", "external_source", "external_id"],
                condition=(
                    models.Q(deleted_at__isnull=True)
                    & ~models.Q(external_source="")
                    & ~models.Q(external_id="")
                ),
                name="uniq_prospect_campaign_external",
            ),
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "campaign"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["campaign", "next_followup_at"]),
            models.Index(fields=["organization_id", "external_source", "external_id"]),
        ]

    def __str__(self) -> str:
        return self.business_name


class ProspectEmailMessage(BaseModel):
    """Email outreach record for prospects, separate from WhatsApp outbound messages."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        BOUNCED = "bounced", "Bounced"

    prospect = models.ForeignKey(
        Prospect,
        on_delete=models.CASCADE,
        related_name="email_messages",
    )
    campaign = models.ForeignKey(
        ProspectingCampaign,
        on_delete=models.CASCADE,
        related_name="email_messages",
    )
    to_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.QUEUED)
    provider_message_id = models.CharField(max_length=255, blank=True)
    idempotency_key = models.CharField(max_length=255)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "prospecting_email_message"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "idempotency_key"],
                name="uniq_prospect_email_idempotency",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["status", "available_at"]),
            models.Index(fields=["organization_id", "to_email"]),
        ]

    def __str__(self) -> str:
        return f"{self.to_email}:{self.status}"
