"""Media Celery workers.

All idempotent and retry-safe: downloads dedupe by reference, transcriptions
dedupe completed results, image generation dedupes completed requests. Failures
stay visible on MediaProcessingJob / the owning model. Queues (settings):
media.download_whatsapp_media + media.process_audio + media.transcribe_audio ->
``transcription``; media.generate_image / store_generated_image ->
``image_generation``; cleanup -> ``ai_slow``.
"""

from celery import shared_task

_RETRY = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 300,
    "max_retries": 3,
    "retry_jitter": True,
}


@shared_task(name="media.download_whatsapp_media", **_RETRY)
def download_whatsapp_media(*, media_reference_id: str):
    from crm.media.services.media_downloader import MediaDownloader

    asset = MediaDownloader.download_from_whatsapp_reference(media_reference_id=media_reference_id)
    return str(asset.id)


@shared_task(name="media.transcribe_audio", **_RETRY)
def transcribe_audio(*, media_asset_id: str, force: bool = False):
    from crm.media.models import MediaAsset
    from crm.media.services.audio_transcription import AudioTranscriptionService

    asset = MediaAsset.objects.get(id=media_asset_id)
    transcription = AudioTranscriptionService.transcribe(media_asset=asset, force=force)
    return str(transcription.id)


@shared_task(name="media.process_audio", **_RETRY)
def process_audio(*, media_asset_id: str):
    from crm.media.models import MediaAsset
    from crm.media.services.audio_processing import AudioProcessingService

    asset = MediaAsset.objects.get(id=media_asset_id)
    transcription = AudioProcessingService.process(media_asset=asset)
    return str(transcription.id)


@shared_task(name="media.generate_image", **_RETRY)
def generate_image(*, image_generation_request_id: str):
    from crm.media.services.image_generation import ImageGenerationService

    result = ImageGenerationService.run_generation(image_generation_request_id)
    return str(result.id)


@shared_task(name="media.store_generated_image", **_RETRY)
def store_generated_image(*, image_generation_request_id: str):
    # Storage happens inside run_generation; this task ensures completion and is
    # idempotent (a completed request is returned as-is).
    from crm.media.services.image_generation import ImageGenerationService

    result = ImageGenerationService.run_generation(image_generation_request_id)
    return str(result.result_media_asset_id) if result.result_media_asset_id else ""


@shared_task(name="media.cleanup_failed_jobs", ignore_result=True)
def cleanup_failed_jobs(*, older_than_hours: int = 24):
    from crm.media.services.media_cleanup import MediaCleanupService

    return MediaCleanupService.cleanup_failed_jobs(older_than_hours=older_than_hours)
