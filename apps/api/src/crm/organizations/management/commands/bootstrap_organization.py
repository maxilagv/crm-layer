import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from crm.core.security.permissions import Role
from crm.organizations.models import Membership, Organization
from crm.organizations.services.organizations import create_organization_for_user


class Command(BaseCommand):
    help = "Create the first owner user and organization for a fresh CRM instance."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", required=True)
        parser.add_argument("--organization", required=True)
        parser.add_argument("--password", default="")

    @transaction.atomic
    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        name = options["name"].strip()
        organization_name = options["organization"].strip()
        password = options["password"]

        if not email or not name or not organization_name:
            raise CommandError("--email, --name and --organization cannot be blank")

        user_model = get_user_model()
        user = user_model.objects.filter(email=email).first()
        created_user = user is None
        if user is None:
            if not password:
                password = getpass.getpass("Password: ")
            if not password:
                raise CommandError("Password is required for a new user")
            user = user_model.objects.create_user(email=email, password=password, name=name)
        else:
            user.name = name
            user.save(update_fields=["name", "updated_at"])

        membership = (
            Membership.objects.filter(
                user=user,
                role=Role.OWNER.value,
                status=Membership.Status.ACTIVE,
            )
            .select_related("organization")
            .first()
        )
        if membership:
            organization = membership.organization
            created_organization = False
        else:
            organization = create_organization_for_user(owner=user, name=organization_name)
            created_organization = True

        Organization.objects.filter(id=organization.id).update(owner=user)
        self.stdout.write(
            self.style.SUCCESS(
                "Bootstrap ready: "
                f"user={user.email} created_user={created_user} "
                f"organization={organization.slug} created_organization={created_organization}"
            )
        )
