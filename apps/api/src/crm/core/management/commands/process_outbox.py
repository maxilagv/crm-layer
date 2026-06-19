from django.core.management.base import BaseCommand

from crm.core.services.outbox import process_outbox_batch


class Command(BaseCommand):
    help = "Process pending outbox events once."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        processed = process_outbox_batch(limit=options["limit"])
        self.stdout.write(self.style.SUCCESS(f"Processed {processed} outbox events"))
