from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from crm.core.models import BaseModel


class OrganizationSettingsBase(BaseModel):
    class Meta:
        abstract = True


class BusinessProfile(OrganizationSettingsBase):
    business_name = models.CharField(max_length=255, blank=True)
    owner_name = models.CharField(max_length=255, blank=True)
    owner_phone = models.CharField(max_length=32, blank=True)
    default_language = models.CharField(max_length=16, default="es")
    timezone = models.CharField(max_length=64, default="America/Argentina/Buenos_Aires")
    business_description = models.TextField(blank=True)
    services_offered = models.JSONField(default=list, blank=True)
    target_clients = models.JSONField(default=list, blank=True)
    brand_tone = models.CharField(max_length=255, blank=True)
    calendar_link = models.URLField(max_length=500, blank=True)
    website_url = models.URLField(max_length=500, blank=True)
    # Owner voice (Phase 9.2): how the owner writes, so the agent sounds like them.
    owner_writing_style = models.TextField(blank=True)
    signature_phrases = models.JSONField(default=list, blank=True)
    # Optional sales handoff contact used by prospecting when a lead shows real interest.
    closer_name = models.CharField(max_length=255, blank=True)
    closer_whatsapp = models.CharField(max_length=32, blank=True)
    closer_role = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "settings_business_profile"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id"],
                name="uniq_business_profile_organization",
                nulls_distinct=False,
            )
        ]
        indexes = [models.Index(fields=["organization_id", "deleted_at"])]


class SalesPolicy(OrganizationSettingsBase):
    main_sales_goal = models.TextField(blank=True)
    call_to_action = models.CharField(max_length=255, blank=True)
    can_quote_prices = models.BooleanField(default=False)
    price_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_policy_text = models.TextField(blank=True)
    must_handoff_for_price = models.BooleanField(default=True)
    common_objections = models.JSONField(default=list, blank=True)
    forbidden_claims = models.JSONField(default=list, blank=True)
    sales_tone = models.CharField(max_length=255, default="professional_consultative")

    class Meta:
        db_table = "settings_sales_policy"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id"],
                name="uniq_sales_policy_organization",
                nulls_distinct=False,
            )
        ]
        indexes = [models.Index(fields=["organization_id", "deleted_at"])]


class SupportPolicy(OrganizationSettingsBase):
    support_hours = models.JSONField(default=dict, blank=True)
    allowed_support_actions = models.JSONField(default=list, blank=True)
    forbidden_support_actions = models.JSONField(default=list, blank=True)
    urgent_keywords = models.JSONField(default=list, blank=True)
    critical_ticket_rules = models.JSONField(default=list, blank=True)
    data_request_policy = models.TextField(blank=True)
    default_support_reply = models.TextField(blank=True)

    class Meta:
        db_table = "settings_support_policy"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id"],
                name="uniq_support_policy_organization",
                nulls_distinct=False,
            )
        ]
        indexes = [models.Index(fields=["organization_id", "deleted_at"])]


class AIBehaviorPolicy(OrganizationSettingsBase):
    class Provider(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        ANTHROPIC = "anthropic", "Anthropic"
        FAKE = "fake", "Fake"

    default_provider = models.CharField(
        max_length=32, choices=Provider.choices, default=Provider.OPENAI
    )
    fallback_provider = models.CharField(
        max_length=32, choices=Provider.choices, null=True, blank=True
    )
    default_sales_model = models.CharField(max_length=120, blank=True)
    default_support_model = models.CharField(max_length=120, blank=True)
    max_context_messages = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(200)],
    )
    temperature_sales = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.40,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
    )
    temperature_support = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.20,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
    )
    auto_reply_enabled = models.BooleanField(default=False)
    human_handoff_required_for_risks = models.BooleanField(default=True)

    class Meta:
        db_table = "settings_ai_behavior_policy"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id"],
                name="uniq_ai_policy_organization",
                nulls_distinct=False,
            )
        ]
        indexes = [models.Index(fields=["organization_id", "deleted_at"])]


class NotificationPolicy(OrganizationSettingsBase):
    notify_on_new_lead = models.BooleanField(default=True)
    notify_on_human_handoff = models.BooleanField(default=True)
    notify_on_failed_ai_reply = models.BooleanField(default=True)
    notification_channels = models.JSONField(default=list, blank=True)
    quiet_hours = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "settings_notification_policy"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id"],
                name="uniq_notification_policy_organization",
                nulls_distinct=False,
            )
        ]
        indexes = [models.Index(fields=["organization_id", "deleted_at"])]


class WhatsAppPolicy(OrganizationSettingsBase):
    auto_reply_enabled = models.BooleanField(default=False)
    business_hours = models.JSONField(default=dict, blank=True)
    handoff_keywords = models.JSONField(default=list, blank=True)
    opt_out_keywords = models.JSONField(default=list, blank=True)
    allowed_outbound_templates = models.JSONField(default=list, blank=True)
    media_download_enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "settings_whatsapp_policy"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id"],
                name="uniq_whatsapp_policy_organization",
                nulls_distinct=False,
            )
        ]
        indexes = [models.Index(fields=["organization_id", "deleted_at"])]


class ProspectingPolicy(OrganizationSettingsBase):
    agent_paused = models.BooleanField(default=False)
    send_start_hour = models.PositiveSmallIntegerField(
        default=9,
        validators=[MinValueValidator(0), MaxValueValidator(23)],
    )
    send_cutoff_hour = models.PositiveSmallIntegerField(
        default=18,
        validators=[MinValueValidator(0), MaxValueValidator(23)],
    )
    org_daily_cap = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "settings_prospecting_policy"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id"],
                name="uniq_prospecting_policy_organization",
                nulls_distinct=False,
            )
        ]
        indexes = [models.Index(fields=["organization_id", "deleted_at"])]
