from django.core.management.base import BaseCommand

from crm.notifications.services.digest_builder import DigestBuilder
from crm.organizations.models import Organization


class Command(BaseCommand):
    help = "Build owner daily notification digests idempotently."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default=None)

    def handle(self, *args, **options):
        organizations = (
            Organization.objects.filter(id=options["organization_id"]).select_related("owner")
            if options["organization_id"]
            else Organization.objects.select_related("owner").all()
        )
        count = 0
        for organization in organizations:
            _, created = DigestBuilder.build_daily(
                organization=organization,
                recipient_user=organization.owner,
            )
            count += int(created)
        self.stdout.write(self.style.SUCCESS(f"{count} digests built"))
