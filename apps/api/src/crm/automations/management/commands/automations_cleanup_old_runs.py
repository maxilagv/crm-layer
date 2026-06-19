from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from crm.automations.models import AutomationRun


class Command(BaseCommand):
    help = "Soft-delete old automation runs."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90)

    def handle(self, *args, **options):
        threshold = timezone.now() - timedelta(days=options["days"])
        count = AutomationRun.objects.filter(created_at__lt=threshold).soft_delete()
        self.stdout.write(self.style.SUCCESS(f"{count} old automation runs archived"))
