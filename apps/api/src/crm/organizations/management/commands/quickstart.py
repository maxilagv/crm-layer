"""One-command local setup so the CRM is usable right after `make dev` + migrate.

Creates the owner user + organization, configures Google Gemini as the AI provider,
seeds the versioned prompts, and fills the business profile (name + owner phone) so
the assistant and reminders work end to end.

    python manage.py quickstart --email yo@ejemplo.com --name "Maxi" \
        --organization "Mi Estudio" --password "secret" --owner-phone 5491137725766
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from crm.business_settings.models import BusinessProfile
from crm.core.security.permissions import Role
from crm.organizations.models import Membership


class Command(BaseCommand):
    help = "Bootstrap a usable instance: owner+org, Gemini provider, prompts, business profile."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", required=True)
        parser.add_argument("--organization", required=True)
        parser.add_argument("--password", default="")
        parser.add_argument("--owner-phone", default="")
        parser.add_argument(
            "--gemini-model",
            default="gemini-2.5-flash",
            help="Default Gemini model for the agent.",
        )

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        name = options["name"].strip()
        org_name = options["organization"].strip()

        # 1) Owner user + organization.
        call_command(
            "bootstrap_organization",
            email=email,
            name=name,
            organization=org_name,
            password=options["password"],
        )
        membership = (
            Membership.objects.filter(
                user__email=email, role=Role.OWNER.value, status=Membership.Status.ACTIVE
            )
            .select_related("organization")
            .first()
        )
        if membership is None:
            raise CommandError("Bootstrap did not produce an owner membership")
        organization = membership.organization

        # 2) Two-provider routing: OpenAI (quality) + Gemini (free bulk), per-purpose roles.
        # OpenAI text purposes stay on free Gemini until OPENAI_API_KEY is set (then re-run).
        call_command("ai_setup_providers", organization_id=str(organization.id))

        # 3) Versioned prompts (idempotent).
        call_command("ai_seed_prompts", organization_id=str(organization.id))

        # 4) Business profile (name + owner phone → assistant + reminders).
        with transaction.atomic():
            profile, _ = BusinessProfile.objects.get_or_create(
                organization_id=organization.id,
                defaults={"business_name": org_name, "owner_name": name},
            )
            dirty = []
            if not profile.business_name:
                profile.business_name = org_name
                dirty.append("business_name")
            if not profile.owner_name:
                profile.owner_name = name
                dirty.append("owner_name")
            if options["owner_phone"]:
                profile.owner_phone = options["owner_phone"].strip()
                dirty.append("owner_phone")
            if dirty:
                profile.save(update_fields=[*dirty, "updated_at"])

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Listo. Org '{organization.slug}' operativa con Gemini + prompts + perfil. "
                "Entra al panel (http://localhost:3000), modulo Tareas, y carga recordatorios. "
                "Para WhatsApp: conecta el numero por QR en Config > WhatsApp."
            )
        )
