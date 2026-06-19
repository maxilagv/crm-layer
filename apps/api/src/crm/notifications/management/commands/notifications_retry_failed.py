from django.core.management.base import BaseCommand

from crm.notifications.services.delivery_retry import DeliveryRetryService
from crm.organizations.models import Organization


class Command(BaseCommand):
    help = "Retry failed notification deliveries."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default=None)

    def handle(self, *args, **options):
        organization = (
            Organization.objects.get(id=options["organization_id"])
            if options["organization_id"]
            else None
        )
        count = DeliveryRetryService.retry_failed(organization=organization)
        self.stdout.write(self.style.SUCCESS(f"{count} deliveries retried"))
