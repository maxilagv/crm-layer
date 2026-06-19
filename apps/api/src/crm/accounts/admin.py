from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import APIKey, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    list_display = ("email", "name", "is_active", "is_staff", "last_login_at")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "name", "phone")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name", "phone", "timezone", "locale")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "last_login_at")}),
        ("Metadata", {"fields": ("metadata",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "prefix", "organization_id", "expires_at", "revoked_at", "created_at")
    list_filter = ("revoked_at",)
    search_fields = ("name", "prefix")
    readonly_fields = ("hashed_key", "last_used_at", "created_at", "updated_at")
