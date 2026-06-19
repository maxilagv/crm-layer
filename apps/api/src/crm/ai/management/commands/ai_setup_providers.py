"""Configure the two-provider setup: OpenAI (paid, quality) + Gemini (free, bulk).

Assigns each AIPurpose a role:
- **OpenAI** (gpt-4o-mini) for quality / customer-facing / owner-voice / tool-using text
  (sales, support, assistant, document_draft, project_brief, outreach_opener, outreach_reply) and
  for the
  modalities only OpenAI covers here (audio transcription, image generation).
- **Gemini** (free, gemini-2.5-flash) for high-volume classification/extraction
  (lead_scoring, task_extraction, conversation_summary, risk_classification,
  audio_ticket_extraction, memory_extraction, prospect_qualification, reply_intent) and
  embeddings (free text-embedding-004).

Budget-safe: OpenAI text purposes fall back to free Gemini, so when the OpenAI balance runs
out (``insufficient_quota`` → RateLimit → retryable) the system keeps working for free.

Key-aware: if ``OPENAI_API_KEY`` is not set in the env, the OpenAI *text* purposes stay on
Gemini (nothing breaks); re-run after setting the key to promote them. Credentials live in the
env (OPENAI_API_KEY / GEMINI_API_KEY), never in the DB.
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from crm.ai.domain.enums import AIProviderType, AIPurpose
from crm.ai.models import AIModelConfig, AIProvider
from crm.organizations.models import Organization

OPENAI = AIProviderType.OPENAI.value
GEMINI = AIProviderType.GEMINI.value

# Purpose -> preferred (provider_type, model). OpenAI text purposes get a Gemini fallback.
ROLE_MAP: dict[str, tuple[str, str]] = {
    # Quality / customer-facing / owner-voice / tool-using -> OpenAI.
    AIPurpose.SALES_REPLY.value: (OPENAI, "gpt-4o-mini"),
    AIPurpose.SUPPORT_REPLY.value: (OPENAI, "gpt-4o-mini"),
    AIPurpose.ASSISTANT_REPLY.value: (OPENAI, "gpt-4o-mini"),
    AIPurpose.DOCUMENT_DRAFT.value: (OPENAI, "gpt-4o-mini"),
    AIPurpose.PROJECT_BRIEF.value: (OPENAI, "gpt-4o-mini"),
    AIPurpose.OUTREACH_OPENER.value: (OPENAI, "gpt-4o-mini"),
    AIPurpose.OUTREACH_REPLY.value: (OPENAI, "gpt-4o-mini"),
    # Modalities only OpenAI covers in this codebase.
    AIPurpose.AUDIO_TRANSCRIPTION.value: (OPENAI, "whisper-1"),
    AIPurpose.IMAGE_GENERATION.value: (OPENAI, "dall-e-3"),
    # High-volume classification / extraction -> free Gemini (protect the budget).
    AIPurpose.LEAD_SCORING.value: (GEMINI, "gemini-2.5-flash"),
    AIPurpose.TASK_EXTRACTION.value: (GEMINI, "gemini-2.5-flash"),
    AIPurpose.CONVERSATION_SUMMARY.value: (GEMINI, "gemini-2.5-flash"),
    AIPurpose.RISK_CLASSIFICATION.value: (GEMINI, "gemini-2.5-flash"),
    AIPurpose.AUDIO_TICKET_EXTRACTION.value: (GEMINI, "gemini-2.5-flash"),
    AIPurpose.MEMORY_EXTRACTION.value: (GEMINI, "gemini-2.5-flash"),
    AIPurpose.PROSPECT_QUALIFICATION.value: (GEMINI, "gemini-2.5-flash"),
    AIPurpose.REPLY_INTENT.value: (GEMINI, "gemini-2.5-flash"),
    # Embeddings -> free Gemini.
    AIPurpose.EMBEDDING.value: (GEMINI, "text-embedding-004"),
}

# OpenAI text purposes that should fall back to free Gemini when OpenAI fails / runs out.
_GEMINI_FALLBACK_PURPOSES = {
    AIPurpose.SALES_REPLY.value,
    AIPurpose.SUPPORT_REPLY.value,
    AIPurpose.ASSISTANT_REPLY.value,
    AIPurpose.DOCUMENT_DRAFT.value,
    AIPurpose.PROJECT_BRIEF.value,
    AIPurpose.OUTREACH_OPENER.value,
    AIPurpose.OUTREACH_REPLY.value,
}
_AUDIO = AIPurpose.AUDIO_TRANSCRIPTION.value
_IMAGE = AIPurpose.IMAGE_GENERATION.value
_EMBEDDING = AIPurpose.EMBEDDING.value
_GEMINI_FALLBACK_MODEL = "gemini-2.5-flash"


class Command(BaseCommand):
    help = "Configura los 2 proveedores (OpenAI calidad + Gemini gratis) con roles por propósito."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default=None)
        parser.add_argument(
            "--force-openai",
            action="store_true",
            help="Activar OpenAI aunque OPENAI_API_KEY no esté seteada (fallará hasta cargarla).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["organization_id"]:
            organizations = Organization.objects.filter(id=options["organization_id"])
        else:
            organizations = Organization.objects.all()

        openai_active = bool(getattr(settings, "OPENAI_API_KEY", "")) or options["force_openai"]

        for organization in organizations:
            openai_provider = self._provider(organization.id, OPENAI, "OpenAI", priority=10)
            gemini_provider = self._provider(organization.id, GEMINI, "Google Gemini", priority=20)
            providers = {OPENAI: openai_provider, GEMINI: gemini_provider}

            on_openai = 0
            on_gemini = 0
            for purpose, (preferred, model) in ROLE_MAP.items():
                provider_type, model_name = preferred, model
                fallback_provider = None
                fallback_model = ""

                if preferred == OPENAI and purpose in _GEMINI_FALLBACK_PURPOSES:
                    if openai_active:
                        fallback_provider = gemini_provider
                        fallback_model = _GEMINI_FALLBACK_MODEL
                    else:
                        # No OpenAI key yet: keep these on free Gemini so nothing breaks.
                        provider_type, model_name = GEMINI, _GEMINI_FALLBACK_MODEL

                provider = providers[provider_type]
                self._activate(
                    organization_id=organization.id,
                    provider=provider,
                    purpose=purpose,
                    model_name=model_name,
                    fallback_provider=fallback_provider,
                    fallback_model=fallback_model,
                )
                if provider_type == OPENAI:
                    on_openai += 1
                else:
                    on_gemini += 1

            self.stdout.write(
                f"{organization.slug}: OpenAI en {on_openai} propósitos, Gemini en {on_gemini} "
                f"(OpenAI {'ACTIVO' if openai_active else 'en espera de OPENAI_API_KEY'})."
            )

        msg = (
            "Proveedores configurados. Poné OPENAI_API_KEY y GEMINI_API_KEY en el .env y reiniciá. "
            "Cuando se agote el saldo de OpenAI, los textos caen solos a Gemini gratis."
        )
        self.stdout.write(self.style.SUCCESS(msg))

    @staticmethod
    def _provider(organization_id, provider_type: str, name: str, *, priority: int) -> AIProvider:
        provider, _ = AIProvider.objects.get_or_create(
            organization_id=organization_id,
            provider_type=provider_type,
            defaults={"name": name, "priority": priority, "is_enabled": True},
        )
        AIProvider.objects.filter(id=provider.id).update(is_enabled=True, priority=priority)
        return provider

    @staticmethod
    def _activate(
        *,
        organization_id,
        provider: AIProvider,
        purpose: str,
        model_name: str,
        fallback_provider: AIProvider | None,
        fallback_model: str,
    ) -> None:
        is_embedding = purpose == _EMBEDDING
        is_audio = purpose == _AUDIO
        is_image = purpose == _IMAGE
        is_text = not (is_embedding or is_audio or is_image)
        # Make this provider the single active config for the purpose.
        AIModelConfig.objects.filter(
            organization_id=organization_id, purpose=purpose, is_active=True
        ).exclude(provider=provider).update(is_active=False)
        AIModelConfig.objects.update_or_create(
            organization_id=organization_id,
            provider=provider,
            purpose=purpose,
            defaults={
                "model_name": model_name,
                "is_active": True,
                "supports_tools": is_text,
                "supports_structured_outputs": is_text,
                "supports_audio": is_audio,
                "supports_images": is_image,
                "supports_embeddings": is_embedding,
                "fallback_provider": fallback_provider,
                "fallback_model": fallback_model,
            },
        )
