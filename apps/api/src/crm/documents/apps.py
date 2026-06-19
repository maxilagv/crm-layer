from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "crm.documents"
    label = "documents"

    def ready(self) -> None:
        # Register the agent tool so the AI can generate documents.
        try:
            from crm.ai.tools import register_tool

            from .ai_tool import GenerateDocumentTool

            register_tool(GenerateDocumentTool())
        except Exception:  # noqa: BLE001 — never block app startup on tool registration
            pass
