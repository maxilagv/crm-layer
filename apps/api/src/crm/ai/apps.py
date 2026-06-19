from django.apps import AppConfig


class AIConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "crm.ai"
    verbose_name = "AI Platform"

    def ready(self) -> None:
        # Register built-in tools on app load so the registry is always populated.
        from crm.ai.tools import register_builtin_tools

        register_builtin_tools()
