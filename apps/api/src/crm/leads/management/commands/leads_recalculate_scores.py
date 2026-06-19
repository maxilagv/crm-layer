from django.core.management.base import BaseCommand

from crm.leads.domain.enums import LeadStatus
from crm.leads.models import Lead
from crm.leads.services.lead_scoring import score_lead


class Command(BaseCommand):
    help = "Recalculate lead scores with deterministic fallback by default."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", dest="organization_id", default="")
        parser.add_argument("--use-ai", action="store_true")

    def handle(self, *args, **options):
        queryset = Lead.objects.filter(status=LeadStatus.ACTIVE.value)
        if options["organization_id"]:
            queryset = queryset.filter(organization_id=options["organization_id"])
        updated = 0
        for lead in queryset.select_related("contact"):
            result = score_lead(lead=lead, use_ai=options["use_ai"])
            updated += int(result.updated)
        self.stdout.write(self.style.SUCCESS(f"Recalculated {updated} leads"))
