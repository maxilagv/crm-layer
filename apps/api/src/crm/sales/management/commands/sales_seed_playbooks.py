from django.core.management.base import BaseCommand, CommandError

from crm.organizations.models import Organization
from crm.sales.services.playbook_service import seed_default_playbooks


class Command(BaseCommand):
    help = "Seed default sales playbooks for one organization or all organizations."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", dest="organization_id", default="")

    def handle(self, *args, **options):
        organization_id = options["organization_id"]
        organizations = Organization.objects.all()
        if organization_id:
            organizations = organizations.filter(id=organization_id)
            if not organizations.exists():
                raise CommandError("Organization not found")
        total = 0
        for organization in organizations:
            total += seed_default_playbooks(organization_id=organization.id)
        self.stdout.write(self.style.SUCCESS(f"Seeded {total} playbooks"))
