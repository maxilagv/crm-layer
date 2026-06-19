from django.contrib import admin

from crm.whatsapp.models import (
    WhatsAppBusinessAccount,
    WhatsAppInboundMessage,
    WhatsAppMediaReference,
    WhatsAppMessageStatus,
    WhatsAppOutboundMessage,
    WhatsAppPhoneNumber,
    WhatsAppTemplate,
    WhatsAppWebhookEvent,
)


@admin.register(WhatsAppBusinessAccount)
class WhatsAppBusinessAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "waba_id", "organization_id", "status", "created_at")
    search_fields = ("name", "waba_id")
    list_filter = ("status",)


@admin.register(WhatsAppPhoneNumber)
class WhatsAppPhoneNumberAdmin(admin.ModelAdmin):
    list_display = (
        "phone_number_id",
        "display_phone_number",
        "organization_id",
        "status",
        "created_at",
    )
    search_fields = ("phone_number_id", "display_phone_number", "verified_name")
    list_filter = ("status",)


@admin.register(WhatsAppWebhookEvent)
class WhatsAppWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "organization_id", "status", "received_at")
    search_fields = ("event_id",)
    list_filter = ("event_type", "status")
    readonly_fields = ("raw_payload", "signature")


@admin.register(WhatsAppInboundMessage)
class WhatsAppInboundMessageAdmin(admin.ModelAdmin):
    list_display = ("external_message_id", "message_type", "organization_id", "status")
    search_fields = ("external_message_id", "wa_id", "from_phone_e164")
    list_filter = ("message_type", "status")


@admin.register(WhatsAppOutboundMessage)
class WhatsAppOutboundMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "message_type", "organization_id", "status", "external_message_id")
    search_fields = ("external_message_id", "recipient_phone_e164", "idempotency_key")
    list_filter = ("message_type", "status")


@admin.register(WhatsAppMessageStatus)
class WhatsAppMessageStatusAdmin(admin.ModelAdmin):
    list_display = ("external_message_id", "status", "organization_id", "status_timestamp")
    search_fields = ("external_message_id",)
    list_filter = ("status",)


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "language", "category", "organization_id", "status")
    search_fields = ("name", "language")
    list_filter = ("category", "status")


@admin.register(WhatsAppMediaReference)
class WhatsAppMediaReferenceAdmin(admin.ModelAdmin):
    list_display = ("external_media_id", "media_type", "organization_id", "status")
    search_fields = ("external_media_id", "file_name", "sha256")
    list_filter = ("media_type", "status")
