from django.contrib import admin

from .models import Client, ClientContact, ClientService, ClientStatusHistory


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("display_name", "status", "support_level", "service_plan", "created_at")
    list_filter = ("status", "support_level", "onboarding_status")
    search_fields = ("display_name", "id", "contact__display_name")
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ClientContact)
class ClientContactAdmin(admin.ModelAdmin):
    list_display = ("client", "contact", "role", "is_primary", "can_request_support")
    list_filter = ("role", "is_primary", "can_request_support")
    search_fields = ("client__display_name", "contact__display_name")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ClientService)
class ClientServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "service_type", "status", "client", "created_at")
    list_filter = ("service_type", "status")
    search_fields = ("name", "client__display_name")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ClientStatusHistory)
class ClientStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("client", "from_status", "to_status", "changed_by_type", "created_at")
    list_filter = ("to_status", "changed_by_type")
    date_hierarchy = "created_at"
    readonly_fields = tuple(f.name for f in ClientStatusHistory._meta.fields)

    def has_add_permission(self, request):
        return False
