from django.core.management.base import BaseCommand

from crm.leads.models import Lead
from crm.sales.services.sales_conversation_agent import notify_owner_for_hot_lead


class Command(BaseCommand):
    help = "Detect hot leads and emit owner notification events idempotently."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", dest="organization_id", default="")

    def handle(self, *args, **options):
        queryset = Lead.objects.filter(score__gte=76)
        if options["organization_id"]:
            queryset = queryset.filter(organization_id=options["organization_id"])
        notified = 0
        for lead in queryset:
            notified += int(notify_owner_for_hot_lead(lead=lead, reason="management_command"))
        self.stdout.write(self.style.SUCCESS(f"Notified {notified} hot leads"))
