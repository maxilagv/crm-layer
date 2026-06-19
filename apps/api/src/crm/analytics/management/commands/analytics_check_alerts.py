from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_date

from crm.analytics.services.alert_service import AlertService
from crm.organizations.models import Organization


class Command(BaseCommand):
    help = "Evaluate analytics alert definitions."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default="")
        parser.add_argument("--date", default="")

    def handle(self, *args, **options):
        day = parse_date(options["date"]) if options["date"] else timezone.localdate()
        organizations = Organization.objects.all()
        if options["organization_id"]:
            organizations = organizations.filter(id=options["organization_id"])
        opened = 0
        for organization in organizations:
            opened += len(AlertService.check_alerts(organization=organization, date=day))
        self.stdout.write(self.style.SUCCESS(f"Opened {opened} alert events"))
