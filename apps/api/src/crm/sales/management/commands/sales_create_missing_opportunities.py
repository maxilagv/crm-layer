from django.core.management.base import BaseCommand

from crm.leads.domain.enums import LeadStatus
from crm.leads.models import Lead
from crm.sales.models import SalesOpportunity
from crm.sales.services.opportunity_service import create_or_update_opportunity_for_lead


class Command(BaseCommand):
    help = "Create opportunities for active/won leads that do not have one."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", dest="organization_id", default="")

    def handle(self, *args, **options):
        queryset = Lead.objects.filter(status__in=[LeadStatus.ACTIVE.value, LeadStatus.WON.value])
        if options["organization_id"]:
            queryset = queryset.filter(organization_id=options["organization_id"])
        created = 0
        for lead in queryset.select_related("contact"):
            exists = SalesOpportunity.objects.filter(
                organization_id=lead.organization_id, lead=lead
            ).exists()
            create_or_update_opportunity_for_lead(lead=lead)
            created += int(not exists)
        self.stdout.write(self.style.SUCCESS(f"Created {created} opportunities"))
