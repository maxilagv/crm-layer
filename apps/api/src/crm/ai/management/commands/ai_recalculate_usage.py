from django.core.management.base import BaseCommand

from crm.ai.tasks import recalculate_usage


class Command(BaseCommand):
    help = "Recalculate estimated costs for all usage records (after pricing updates)."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default=None)

    def handle(self, *args, **options):
        updated = recalculate_usage(organization_id=options["organization_id"])
        self.stdout.write(self.style.SUCCESS(f"Recalculated {updated} usage records"))
