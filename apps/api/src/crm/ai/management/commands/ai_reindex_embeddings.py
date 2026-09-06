"""Re-enqueue legacy embeddings whose pgvector value is missing."""

from django.core.management.base import BaseCommand

from crm.ai.models import AIEmbedding
from crm.ai.tasks import create_embeddings


class Command(BaseCommand):
    help = (
        "Reindex AIEmbedding rows with vector=NULL, or every row with --all. "
        "Uses source_text, which is capped at 4000 chars; legacy long messages are lossy, "
        "while knowledge chunks (<=1000 chars) are exact."
    )

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default=None)
        parser.add_argument("--all", action="store_true", dest="all_rows")
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        queryset = AIEmbedding.objects.all().order_by("organization_id", "created_at")
        if options["organization_id"]:
            queryset = queryset.filter(organization_id=options["organization_id"])
        if not options["all_rows"]:
            queryset = queryset.filter(vector__isnull=True)

        batch_size = max(1, int(options["batch_size"] or 100))
        enqueued = 0
        for embedding in queryset.iterator(chunk_size=batch_size):
            if not embedding.source_text:
                continue
            metadata = {"force_reindex": True} if options["all_rows"] else None
            create_embeddings.delay(
                organization_id=str(embedding.organization_id),
                owner_type=embedding.owner_type,
                owner_id=str(embedding.owner_id),
                text=embedding.source_text,
                metadata=metadata,
            )
            enqueued += 1
            if enqueued % batch_size == 0:
                self.stdout.write(f"Enqueued {enqueued} embeddings...")

        self.stdout.write(self.style.SUCCESS(f"Enqueued {enqueued} embeddings for reindexing."))
