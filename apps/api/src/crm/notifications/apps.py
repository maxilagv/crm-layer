from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "crm.notifications"
    verbose_name = "Notifications"

    def ready(self) -> None:
        # Register outbox handlers (owner WhatsApp delivery via the bridge).
        try:
            from crm.notifications import outbox_handlers  # noqa: F401
        except Exception:  # noqa: BLE001 — never block app startup on handler import
            pass
