from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "crm.accounts"
    label = "accounts"
    verbose_name = "Accounts"

    def ready(self):
        import crm.accounts.schema  # noqa: F401
