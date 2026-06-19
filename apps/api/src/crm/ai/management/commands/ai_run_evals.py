import json

from django.core.management.base import BaseCommand, CommandError

from crm.ai.services.eval_runner import SUITES, EvalRunner
from crm.organizations.models import Organization


class Command(BaseCommand):
    help = "Run AI eval suites (deterministic; no real providers)."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", required=True)
        parser.add_argument("--suite", default=None, choices=sorted(SUITES))

    def handle(self, *args, **options):
        organization = Organization.objects.filter(id=options["organization_id"]).first()
        if organization is None:
            raise CommandError("Organization not found")
        if options["suite"]:
            report = EvalRunner.run_suite(
                organization_id=organization.id, suite_name=options["suite"]
            )
        else:
            report = EvalRunner.run_all(organization_id=organization.id)
        self.stdout.write(json.dumps(report, indent=2, default=str))
