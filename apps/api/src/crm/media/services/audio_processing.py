"""AudioProcessingService: orchestrate validate -> transcribe for an audio asset.

Ticket extraction from audio is triggered separately (support.create_ticket_from_audio)
so a long transcription never blocks, and so callers without support context can
still transcribe. Chunking for very large files is a documented next step:
``MAX_INLINE_AUDIO_SECONDS`` marks where a splitting strategy would kick in.
"""

from crm.media.domain.exceptions import TranscriptionNotAudio
from crm.media.domain.rules import is_audio_mime

from .audio_transcription import AudioTranscriptionService

# Above this, a future implementation should chunk the audio before transcribing.
MAX_INLINE_AUDIO_SECONDS = 600


class AudioProcessingService:
    @staticmethod
    def process(*, media_asset, force: bool = False):
        if not is_audio_mime(media_asset.mime_type):
            raise TranscriptionNotAudio(f"Asset {media_asset.id} is not audio")
        return AudioTranscriptionService.transcribe(media_asset=media_asset, force=force)
