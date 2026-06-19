from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_date

from crm.analytics.services.daily_summary_builder import DailySummaryBuilder
from crm.organizations.models import Organization


class Command(BaseCommand):
    help = "Build daily analytics summaries and metric snapshots."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default="")
        parser.add_argument("--date", default="")

    def handle(self, *args, **options):
        day = parse_date(options["date"]) if options["date"] else timezone.localdate()
        organizations = Organization.objects.all()
        if options["organization_id"]:
            organizations = organizations.filter(id=options["organization_id"])
        count = 0
        for organization in organizations:
            DailySummaryBuilder.build(organization=organization, date=day)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Built daily metrics for {count} organizations"))
