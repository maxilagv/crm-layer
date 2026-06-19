import json

from django.core.management.base import BaseCommand

from crm.automations.services.trigger_dispatcher import TriggerDispatcher
from crm.organizations.models import Organization


class Command(BaseCommand):
    help = "Dispatch an automation event."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", required=True)
        parser.add_argument("--trigger-type", required=True)
        parser.add_argument("--payload-json", default="{}")
        parser.add_argument("--trigger-event-id", default="")

    def handle(self, *args, **options):
        organization = Organization.objects.get(id=options["organization_id"])
        payload = json.loads(options["payload_json"])
        runs = TriggerDispatcher.dispatch(
            organization=organization,
            trigger_type=options["trigger_type"],
            payload=payload,
            trigger_event_id=options["trigger_event_id"],
        )
        self.stdout.write(self.style.SUCCESS(f"{len(runs)} automation runs dispatched"))
