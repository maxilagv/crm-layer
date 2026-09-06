from django.contrib import admin

from .models import KnowledgeChunk, KnowledgeDocument, KnowledgeSource


@admin.register(KnowledgeSource)
class KnowledgeSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "status", "organization_id", "created_at")
    list_filter = ("source_type", "status")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "ingest_status", "organization_id", "created_at")
    list_filter = ("ingest_status", "source__source_type")
    search_fields = ("title", "raw_text")
    readonly_fields = ("id", "content_hash", "created_at", "updated_at")


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "token_estimate", "organization_id")
    search_fields = ("content",)
    readonly_fields = ("id", "content_hash", "created_at", "updated_at")
