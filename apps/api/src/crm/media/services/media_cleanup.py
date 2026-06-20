"""MediaCleanup: retry-able housekeeping for failed jobs and deleted assets."""

import logging

from django.utils import timezone

from crm.media.domain.enums import MediaStatus, ProcessingJobStatus
from crm.media.models import MediaAsset, MediaProcessingJob

from .media_storage import MediaStorageService

logger = logging.getLogger(__name__)


class MediaCleanupService:
    @staticmethod
    def cleanup_failed_jobs(*, older_than_hours: int = 24) -> int:
        """Cancel stuck/old failed jobs so they stop being retried indefinitely."""
        from datetime import timedelta

        threshold = timezone.now() - timedelta(hours=older_than_hours)
        return MediaProcessingJob.objects.filter(
            status=ProcessingJobStatus.FAILED, updated_at__lt=threshold
        ).update(status=ProcessingJobStatus.CANCELLED, updated_at=timezone.now())

    @staticmethod
    def cleanup_deleted_assets() -> int:
        """Remove stored bytes for assets soft-deleted at the model level."""
        removed = 0
        for asset in MediaAsset.all_objects.filter(deleted_at__isnull=False).exclude(
            status=MediaStatus.DELETED
        ):
            try:
                MediaStorageService.delete_asset_file(asset)
            except Exception:  # pragma: no cover - best effort
                logger.warning(
                    "Failed to delete stored file",
                    extra={
                        "event": "media.cleanup_failed",
                        "metadata": {"asset_id": str(asset.id)},
                    },
                )
                continue
            asset.status = MediaStatus.DELETED
            asset.storage_key = ""
            asset.save(update_fields=["status", "storage_key", "updated_at"])
            removed += 1
        return removed
