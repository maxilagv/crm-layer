"""TranscriptionService: resolve audio bytes from a WhatsApp media reference.

Phase 4 stores media references; this service feeds their bytes into the
gateway. If the media has not been downloaded yet, it fails with a controlled
error instead of pretending.
"""

from crm.ai.domain.exceptions import AIProviderInvalidRequest
from crm.ai.domain.result import AIGatewayResult


class TranscriptionService:
    @staticmethod
    def transcribe_media_reference(*, media_reference_id) -> AIGatewayResult:
        from crm.whatsapp.models import WhatsAppMediaReference

        from .ai_gateway import AIGateway

        reference = WhatsAppMediaReference.objects.filter(id=media_reference_id).first()
        if reference is None:
            raise AIProviderInvalidRequest("Media reference not found")

        audio_bytes = _resolve_bytes(reference)
        if not audio_bytes:
            raise AIProviderInvalidRequest(
                "Media has no downloaded content yet; run the media download task first"
            )
        mime = (getattr(reference, "mime_type", "") or "audio/ogg").split("/")[-1]
        return AIGateway.transcribe_audio(
            organization_id=reference.organization_id,
            audio_bytes=audio_bytes,
            audio_format=mime,
            media_reference_id=reference.id,
        )


def _resolve_bytes(reference) -> bytes | None:
    # The Phase 4 media model may expose a storage path or inline content
    # depending on its download state; support both without hard coupling.
    for attribute in ("local_path", "file_path", "storage_path"):
        path = getattr(reference, attribute, "")
        if path:
            try:
                with open(path, "rb") as handle:
                    return handle.read()
            except OSError:
                return None
    content = getattr(reference, "content", None)
    return bytes(content) if content else None
