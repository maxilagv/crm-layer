import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.config.settings.local")

app = Celery("ai_crm")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Register request/correlation context propagation signals.
import crm.core.observability.celery  # noqa: E402,F401
