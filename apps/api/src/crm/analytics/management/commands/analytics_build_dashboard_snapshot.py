from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from crm.analytics.services.dashboard_builder import DashboardBuilder
from crm.organizations.models import Organization


class Command(BaseCommand):
    help = "Build analytics dashboard snapshots."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default="")
        parser.add_argument("--start-date", default="")
        parser.add_argument("--end-date", default="")

    def handle(self, *args, **options):
        organizations = Organization.objects.all()
        if options["organization_id"]:
            organizations = organizations.filter(id=options["organization_id"])
        count = 0
        for organization in organizations:
            DashboardBuilder.snapshot(
                organization=organization,
                start_date=parse_date(options["start_date"]) if options["start_date"] else None,
                end_date=parse_date(options["end_date"]) if options["end_date"] else None,
            )
            count += 1
        self.stdout.write(
            self.style.SUCCESS(f"Built dashboard snapshots for {count} organizations")
        )
