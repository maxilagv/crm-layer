"""Configure Google Gemini as the active AI provider for an organization.

Creates (idempotently) a Gemini provider and the active model-configs the router
needs, and deactivates competing configs so Gemini is the one selected. Audio
transcription and image generation are skipped (not supported via Gemini's
OpenAI-compatible endpoint). Remember to set GEMINI_API_KEY in the backend env.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from crm.ai.domain.enums import AIProviderType, AIPurpose
from crm.ai.models import AIModelConfig, AIProvider
from crm.organizations.models import Organization

# Gemini's OpenAI-compat layer does not cover these purposes.
SKIP = {AIPurpose.AUDIO_TRANSCRIPTION.value, AIPurpose.IMAGE_GENERATION.value}


class Command(BaseCommand):
    help = "Configura Google Gemini como proveedor activo (provider + model-configs por propósito)."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default=None)
        parser.add_argument("--model", default="gemini-2.5-flash")
        parser.add_argument("--embedding-model", default="text-embedding-004")
        parser.add_argument("--priority", type=int, default=10)

    @transaction.atomic
    def handle(self, *args, **options):
        if options["organization_id"]:
            organizations = Organization.objects.filter(id=options["organization_id"])
        else:
            organizations = Organization.objects.all()

        model = options["model"]
        embedding_model = options["embedding_model"]
        priority = options["priority"]

        for organization in organizations:
            provider, _ = AIProvider.objects.get_or_create(
                organization_id=organization.id,
                provider_type=AIProviderType.GEMINI.value,
                defaults={"name": "Google Gemini", "priority": priority, "is_enabled": True},
            )
            AIProvider.objects.filter(id=provider.id).update(is_enabled=True, priority=priority)

            count = 0
            for purpose in AIPurpose.values:
                if purpose in SKIP:
                    continue
                is_embedding = purpose == AIPurpose.EMBEDDING.value
                # Make Gemini the single active config for this purpose.
                AIModelConfig.objects.filter(
                    organization_id=organization.id, purpose=purpose, is_active=True
                ).exclude(provider=provider).update(is_active=False)
                AIModelConfig.objects.update_or_create(
                    organization_id=organization.id,
                    provider=provider,
                    purpose=purpose,
                    defaults={
                        "model_name": embedding_model if is_embedding else model,
                        "is_active": True,
                        "supports_tools": not is_embedding,
                        "supports_structured_outputs": not is_embedding,
                        "supports_embeddings": is_embedding,
                    },
                )
                count += 1
            self.stdout.write(
                f"{organization.slug}: Gemini activo en {count} propósitos (modelo {model})"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Gemini configurado. Poné GEMINI_API_KEY en el .env del backend y reiniciá."
            )
        )
