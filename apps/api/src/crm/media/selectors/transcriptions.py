"""Read-side queries for transcriptions."""

from crm.media.domain.enums import TranscriptionStatus
from crm.media.models import Transcription


def completed_transcription_for_asset(organization_id, media_asset_id) -> Transcription | None:
    return (
        Transcription.objects.filter(
            organization_id=organization_id,
            media_asset_id=media_asset_id,
            status=TranscriptionStatus.COMPLETED,
        )
        .order_by("-created_at")
        .first()
    )


def transcriptions_for_asset(organization, media_asset_id):
    return Transcription.objects.filter(
        organization_id=organization.id, media_asset_id=media_asset_id
    ).order_by("-created_at")
