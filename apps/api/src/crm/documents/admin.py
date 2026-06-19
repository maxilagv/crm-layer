from django.contrib import admin

from .models import BrandKit, GeneratedDocument


@admin.register(BrandKit)
class BrandKitAdmin(admin.ModelAdmin):
    list_display = ("business_name", "organization_id", "currency", "updated_at")
    search_fields = ("business_name", "organization_id")


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "doc_type", "doc_format", "status", "organization_id", "created_at")
    list_filter = ("doc_type", "doc_format", "status")
    search_fields = ("title", "organization_id")
    readonly_fields = ("created_at", "updated_at")
