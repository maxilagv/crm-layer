from django.core.management.base import BaseCommand

from crm.organizations.models import Organization
from crm.tasks.services.task_reminder import TaskReminderService


class Command(BaseCommand):
    help = "Send due task reminders idempotently."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default=None)

    def handle(self, *args, **options):
        organization = (
            Organization.objects.get(id=options["organization_id"])
            if options["organization_id"]
            else None
        )
        count = TaskReminderService.send_due(organization=organization)
        self.stdout.write(self.style.SUCCESS(f"{count} reminders sent"))
