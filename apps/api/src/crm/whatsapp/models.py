from django.db import models
from django.utils import timezone

from crm.contacts.models import Contact
from crm.conversations.models import Conversation, Message, MessageAttachment
from crm.core.models import BaseModel
from crm.whatsapp.domain.enums import (
    BridgeOutboundStatus,
    InboundMessageStatus,
    MediaReferenceStatus,
    OutboundMessageStatus,
    WebhookEventStatus,
    WebhookEventType,
    WhatsAppAccountStatus,
    WhatsAppDeliveryStatus,
    WhatsAppMessageType,
    WhatsAppPhoneNumberStatus,
    WhatsAppTemplateCategory,
    WhatsAppTemplateStatus,
)


class WhatsAppBusinessAccount(BaseModel):
    waba_id = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=32,
        choices=WhatsAppAccountStatus.choices,
        default=WhatsAppAccountStatus.ACTIVE,
    )

    class Meta:
        db_table = "whatsapp_business_account"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "waba_id"],
                name="uniq_whatsapp_business_account_org_waba",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name}:{self.waba_id}"


class WhatsAppPhoneNumber(BaseModel):
    business_account = models.ForeignKey(
        WhatsAppBusinessAccount,
        on_delete=models.PROTECT,
        related_name="phone_numbers",
    )
    phone_number_id = models.CharField(max_length=64)
    display_phone_number = models.CharField(max_length=64, blank=True)
    verified_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=32,
        choices=WhatsAppPhoneNumberStatus.choices,
        default=WhatsAppPhoneNumberStatus.ACTIVE,
    )

    class Meta:
        db_table = "whatsapp_phone_number"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "phone_number_id"],
                name="uniq_whatsapp_phone_number_org_external",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["phone_number_id"]),
        ]

    def clean(self):
        if self.business_account_id:
            self.organization_id = self.business_account.organization_id

    def save(self, *args, **kwargs):
        if self.business_account_id:
            self.organization_id = self.business_account.organization_id
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.display_phone_number or self.phone_number_id


class WhatsAppWebhookEvent(BaseModel):
    event_id = models.CharField(max_length=128)
    event_type = models.CharField(
        max_length=32,
        choices=WebhookEventType.choices,
        default=WebhookEventType.UNKNOWN,
    )
    raw_payload = models.JSONField(default=dict)
    signature = models.CharField(max_length=128, blank=True)
    status = models.CharField(
        max_length=32,
        choices=WebhookEventStatus.choices,
        default=WebhookEventStatus.RECEIVED,
    )
    received_at = models.DateTimeField(default=timezone.now, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "whatsapp_webhook_event"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "event_id"],
                name="uniq_whatsapp_webhook_event_org_event",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status", "received_at"]),
            models.Index(fields=["organization_id", "event_type"]),
            models.Index(fields=["event_id"]),
        ]

    def mark_processed(self) -> None:
        self.status = WebhookEventStatus.PROCESSED
        self.processed_at = timezone.now()
        self.error_message = ""
        self.save(update_fields=["status", "processed_at", "error_message", "updated_at"])

    def mark_ignored(self, reason: str = "") -> None:
        self.status = WebhookEventStatus.IGNORED
        self.processed_at = timezone.now()
        self.error_message = reason[:2000]
        self.save(update_fields=["status", "processed_at", "error_message", "updated_at"])

    def mark_failed(self, error: Exception | str) -> None:
        self.status = WebhookEventStatus.FAILED
        self.error_message = str(error)[:2000]
        self.processed_at = timezone.now()
        self.save(update_fields=["status", "error_message", "processed_at", "updated_at"])

    def __str__(self) -> str:
        return f"{self.event_type}:{self.event_id}"


class WhatsAppInboundMessage(BaseModel):
    webhook_event = models.ForeignKey(
        WhatsAppWebhookEvent,
        on_delete=models.PROTECT,
        related_name="inbound_messages",
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="whatsapp_inbound_messages",
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="whatsapp_inbound_messages",
    )
    crm_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="whatsapp_inbound_messages",
    )
    phone_number = models.ForeignKey(
        WhatsAppPhoneNumber,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inbound_messages",
    )
    from_phone_e164 = models.CharField(max_length=20, blank=True)
    wa_id = models.CharField(max_length=64, blank=True)
    external_message_id = models.CharField(max_length=255)
    message_type = models.CharField(
        max_length=32,
        choices=WhatsAppMessageType.choices,
        default=WhatsAppMessageType.UNSUPPORTED,
    )
    body = models.TextField(blank=True)
    raw_message = models.JSONField(default=dict, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=InboundMessageStatus.choices,
        default=InboundMessageStatus.RECEIVED,
    )
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "whatsapp_inbound_message"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "external_message_id"],
                name="uniq_whatsapp_inbound_org_external_message",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "conversation", "received_at"]),
            models.Index(fields=["organization_id", "contact", "received_at"]),
            models.Index(fields=["organization_id", "external_message_id"]),
            models.Index(fields=["webhook_event"]),
        ]

    def __str__(self) -> str:
        return self.external_message_id


class WhatsAppOutboundMessage(BaseModel):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="whatsapp_outbound_messages",
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="whatsapp_outbound_messages",
    )
    crm_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="whatsapp_outbound_messages",
    )
    phone_number = models.ForeignKey(
        WhatsAppPhoneNumber,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="outbound_messages",
    )
    message_type = models.CharField(
        max_length=32,
        choices=WhatsAppMessageType.choices,
        default=WhatsAppMessageType.TEXT,
    )
    body = models.TextField(blank=True)
    template_name = models.CharField(max_length=255, blank=True)
    external_message_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=32,
        choices=OutboundMessageStatus.choices,
        default=OutboundMessageStatus.QUEUED,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)
    recipient_phone_e164 = models.CharField(max_length=20)
    payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    queued_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "whatsapp_outbound_message"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "idempotency_key"],
                condition=models.Q(idempotency_key__gt=""),
                name="uniq_whatsapp_outbound_org_idempotency_key",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "external_message_id"]),
            models.Index(fields=["organization_id", "status", "created_at"]),
            models.Index(fields=["organization_id", "conversation", "created_at"]),
            models.Index(fields=["organization_id", "contact", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.message_type}:{self.id}"


class OutboundMessage(BaseModel):
    """Pull-based outbound queue consumed by the local whatsapp-web.js bridge."""

    contact_phone = models.CharField(max_length=20)
    body = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=BridgeOutboundStatus.choices,
        default=BridgeOutboundStatus.PENDING,
    )
    idempotency_key = models.CharField(max_length=255)
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_reason = models.TextField(blank=True)
    prospect_id = models.UUIDField(null=True, blank=True)
    conversation_id = models.UUIDField(null=True, blank=True)
    contact_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "whatsapp_outbound_message_queue"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "idempotency_key"],
                name="uniq_bridge_outbound_org_idempotency",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status", "available_at"]),
            models.Index(fields=["organization_id", "conversation_id"]),
            models.Index(fields=["organization_id", "contact_id"]),
        ]

    def __str__(self) -> str:
        return f"bridge-outbound:{self.id}:{self.status}"


class WhatsAppMessageStatus(BaseModel):
    outbound_message = models.ForeignKey(
        WhatsAppOutboundMessage,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="delivery_statuses",
    )
    external_message_id = models.CharField(max_length=255)
    status = models.CharField(
        max_length=32,
        choices=WhatsAppDeliveryStatus.choices,
        default=WhatsAppDeliveryStatus.UNKNOWN,
    )
    status_timestamp = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    raw_status = models.JSONField(default=dict, blank=True)
    webhook_event = models.ForeignKey(
        WhatsAppWebhookEvent,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="message_statuses",
    )

    class Meta:
        db_table = "whatsapp_message_status"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "external_message_id", "status", "status_timestamp"],
                name="uniq_whatsapp_message_status_org_external_status_ts",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "external_message_id"]),
            models.Index(fields=["outbound_message", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.external_message_id}:{self.status}"


class WhatsAppTemplate(BaseModel):
    name = models.CharField(max_length=255)
    language = models.CharField(max_length=32)
    category = models.CharField(
        max_length=32,
        choices=WhatsAppTemplateCategory.choices,
        default=WhatsAppTemplateCategory.UTILITY,
    )
    status = models.CharField(
        max_length=32,
        choices=WhatsAppTemplateStatus.choices,
        default=WhatsAppTemplateStatus.DRAFT,
    )
    components = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "whatsapp_template"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "name", "language"],
                name="uniq_whatsapp_template_org_name_language",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "category"]),
        ]

    def __str__(self) -> str:
        return f"{self.name}:{self.language}"


class WhatsAppMediaReference(BaseModel):
    webhook_event = models.ForeignKey(
        WhatsAppWebhookEvent,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="media_references",
    )
    inbound_message = models.ForeignKey(
        WhatsAppInboundMessage,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="media_references",
    )
    crm_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="whatsapp_media_references",
    )
    crm_attachment = models.ForeignKey(
        MessageAttachment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="whatsapp_media_references",
    )
    external_media_id = models.CharField(max_length=255)
    media_type = models.CharField(
        max_length=32,
        choices=WhatsAppMessageType.choices,
        default=WhatsAppMessageType.UNSUPPORTED,
    )
    mime_type = models.CharField(max_length=120, blank=True)
    sha256 = models.CharField(max_length=128, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=MediaReferenceStatus.choices,
        default=MediaReferenceStatus.RECEIVED,
    )
    downloaded_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "whatsapp_media_reference"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "external_media_id"],
                name="uniq_whatsapp_media_reference_org_external_media",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status", "created_at"]),
            models.Index(fields=["organization_id", "external_media_id"]),
            models.Index(fields=["inbound_message"]),
        ]

    def __str__(self) -> str:
        return f"{self.media_type}:{self.external_media_id}"
