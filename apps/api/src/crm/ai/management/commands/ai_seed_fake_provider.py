from django.core.management.base import BaseCommand

from crm.ai.domain.enums import AIProviderType, AIPurpose
from crm.ai.models import AIModelConfig, AIProvider
from crm.organizations.models import Organization

_MEDIA_FLAGS = {
    AIPurpose.AUDIO_TRANSCRIPTION.value: {"supports_audio": True},
    AIPurpose.IMAGE_GENERATION.value: {"supports_images": True},
    AIPurpose.EMBEDDING.value: {"supports_embeddings": True},
}


class Command(BaseCommand):
    help = "Create a fake AI provider + model configs for every purpose (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default=None)

    def handle(self, *args, **options):
        if options["organization_id"]:
            organizations = Organization.objects.filter(id=options["organization_id"])
        else:
            organizations = Organization.objects.all()
        for organization in organizations:
            provider, _ = AIProvider.objects.get_or_create(
                organization_id=organization.id,
                provider_type=AIProviderType.FAKE,
                defaults={"name": "Fake provider", "priority": 100},
            )
            created = 0
            for purpose in AIPurpose.values:
                flags = {
                    "supports_tools": True,
                    "supports_structured_outputs": True,
                    **_MEDIA_FLAGS.get(purpose, {}),
                }
                _, was_created = AIModelConfig.objects.get_or_create(
                    organization_id=organization.id,
                    provider=provider,
                    purpose=purpose,
                    defaults={"model_name": "fake-model", "is_active": True, **flags},
                )
                created += int(was_created)
            self.stdout.write(f"{organization.slug}: {created} model configs created")
        self.stdout.write(self.style.SUCCESS("Fake provider seeded"))
