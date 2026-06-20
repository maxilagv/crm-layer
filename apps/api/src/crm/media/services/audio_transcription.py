"""AudioTranscriptionService: transcribe an audio MediaAsset via AIGateway.

Never calls a provider directly. Validates the asset is audio, deduplicates
completed transcriptions (unless ``force``), records a MediaProcessingJob, and
stores provider/model/ai_run_id. Failures are retryable.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from crm.audit.services import audit_event_create
from crm.core.services.outbox import create_outbox_event
from crm.media.domain import events
from crm.media.domain.enums import (
    MediaStatus,
    ProcessingJobStatus,
    ProcessingJobType,
    TranscriptionStatus,
)
from crm.media.domain.exceptions import RetryableMediaError, TranscriptionNotAudio
from crm.media.domain.rules import is_audio_mime
from crm.media.models import MediaProcessingJob, Transcription
from crm.media.selectors.transcriptions import completed_transcription_for_asset

from ._support import org_stub
from .media_storage import MediaStorageService


class AudioTranscriptionService:
    @staticmethod
    def transcribe(*, media_asset, force: bool = False, actor=None, request=None) -> Transcription:
        if not is_audio_mime(media_asset.mime_type):
            raise TranscriptionNotAudio(
                f"MediaAsset {media_asset.id} is not audio ({media_asset.mime_type})"
            )

        if not force:
            existing = completed_transcription_for_asset(
                media_asset.organization_id, media_asset.id
            )
            if existing is not None:
                return existing

        with transaction.atomic():
            transcription = Transcription.objects.create(
                organization_id=media_asset.organization_id,
                media_asset=media_asset,
                status=TranscriptionStatus.PROCESSING,
            )
            job = MediaProcessingJob.objects.create(
                organization_id=media_asset.organization_id,
                media_asset=media_asset,
                job_type=ProcessingJobType.TRANSCRIBE,
                status=ProcessingJobStatus.RUNNING,
                started_at=timezone.now(),
            )

        try:
            from crm.ai.services.ai_gateway import AIGateway

            audio_bytes = MediaStorageService.open_asset(media_asset)
            audio_format = (media_asset.mime_type or "audio/ogg").split("/")[-1]
            result = AIGateway.transcribe_audio(
                organization_id=media_asset.organization_id,
                audio_bytes=audio_bytes,
                audio_format=audio_format,
                media_reference_id=media_asset.id,
            )
        except Exception as exc:
            AudioTranscriptionService._fail(transcription, job, str(exc))
            raise RetryableMediaError(str(exc)) from exc

        if not result.succeeded:
            AudioTranscriptionService._fail(transcription, job, result.error_message or "ai_failed")
            raise RetryableMediaError(result.error_message or "transcription_failed")

        data = result.data or {}
        with transaction.atomic():
            transcription.text = data.get("text", "")
            transcription.language = data.get("language", "es")
            transcription.duration_seconds = Decimal(str(data.get("audio_seconds", "0") or "0"))
            transcription.provider = result.provider
            transcription.model = result.model
            transcription.ai_run_id = result.run_id
            transcription.status = TranscriptionStatus.COMPLETED
            transcription.save()
            job.status = ProcessingJobStatus.SUCCESS
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "finished_at", "updated_at"])
            if media_asset.status == MediaStatus.STORED:
                media_asset.status = MediaStatus.PROCESSED
                media_asset.save(update_fields=["status", "updated_at"])
            create_outbox_event(
                event_type=events.AUDIO_TRANSCRIBED,
                organization_id=media_asset.organization_id,
                payload={
                    "event_type": events.AUDIO_TRANSCRIBED,
                    "organization_id": str(media_asset.organization_id),
                    "data": {
                        "media_asset_id": str(media_asset.id),
                        "transcription_id": str(transcription.id),
                    },
                    "metadata": {},
                },
            )
        if actor is not None:
            audit_event_create(
                event_type="media_audio_transcribed",
                actor=actor,
                organization=org_stub(media_asset.organization_id),
                request=request,
                resource_type="media_transcription",
                resource_id=str(transcription.id),
            )
        return transcription

    @staticmethod
    def _fail(transcription, job, error: str) -> None:
        with transaction.atomic():
            transcription.status = TranscriptionStatus.FAILED
            transcription.error_message = error[:500]
            transcription.save(update_fields=["status", "error_message", "updated_at"])
            job.status = ProcessingJobStatus.FAILED
            job.error_message = error[:500]
            job.attempts = job.attempts + 1
            job.finished_at = timezone.now()
            job.save(
                update_fields=["status", "error_message", "attempts", "finished_at", "updated_at"]
            )
