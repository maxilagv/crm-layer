from django.core.management.base import BaseCommand

from crm.ai.prompts.loader import PromptLoader
from crm.organizations.models import Organization


class Command(BaseCommand):
    help = (
        "Seed (idempotent) or update the AI prompts for one or all organizations. "
        "Use --update to adopt repo changes as a new active version."
    )

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default=None)
        parser.add_argument(
            "--update",
            action="store_true",
            help="Create a new version where the repo content differs from the active one.",
        )
        parser.add_argument(
            "--no-activate",
            action="store_true",
            help="With --update, leave new versions as draft instead of activating them.",
        )

    def handle(self, *args, **options):
        if options["organization_id"]:
            organizations = Organization.objects.filter(id=options["organization_id"])
        else:
            organizations = Organization.objects.all()

        action = "updated" if options["update"] else "created"
        total = 0
        for organization in organizations:
            if options["update"]:
                touched = PromptLoader.update_organization(
                    organization.id, activate=not options["no_activate"]
                )
            else:
                touched = PromptLoader.seed_organization(organization.id)
            total += len(touched)
            if touched:
                self.stdout.write(f"{organization.slug}: {action} {', '.join(touched)}")

        self.stdout.write(self.style.SUCCESS(f"Done. {total} prompt(s) {action}."))
