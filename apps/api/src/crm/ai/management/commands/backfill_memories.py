"""Extract long-term memory from recent conversations (Phase 9.1).

Runs the MEMORY_EXTRACTION purpose over conversations that have enough messages
and persists the facts as ConversationMemory rows, so future replies remember
the contact. Idempotent: ``persist_extracted_facts`` skips duplicate contents.

    python manage.py backfill_memories
    python manage.py backfill_memories --organization-id <uuid> --min-messages 4 --limit 100
"""

from django.core.management.base import BaseCommand
from django.db.models import Count

from crm.ai.tasks import extract_conversation_memory
from crm.conversations.models import Conversation


class Command(BaseCommand):
    help = "Extrae memoria de largo plazo de las conversaciones recientes."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default=None)
        parser.add_argument("--min-messages", type=int, default=4)
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        qs = Conversation.objects.all()
        if options["organization_id"]:
            qs = qs.filter(organization_id=options["organization_id"])
        qs = (
            qs.annotate(n_messages=Count("messages"))
            .filter(n_messages__gte=options["min_messages"])
            .order_by("-last_message_at")[: options["limit"]]
        )

        processed = 0
        for conversation in qs:
            try:
                extract_conversation_memory(conversation_id=str(conversation.id))
                processed += 1
            except Exception as exc:  # noqa: BLE001 — one bad conversation never aborts the batch
                self.stderr.write(f"  conv {conversation.id}: {type(exc).__name__}: {exc}")
        self.stdout.write(self.style.SUCCESS(f"Memoria procesada en {processed} conversación(es)."))
