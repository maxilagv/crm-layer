"""TicketFromAudioService: transcription -> validated AI extraction -> ticket.

Never parses free text: the ticket is built from the AIGateway's structured,
schema-validated ``extract_ticket_from_audio`` output. If the AI output is
invalid, no ticket is created and the failure is surfaced. The source audio is
attached and urgent/critical tickets notify the owner (handled by the creator).
"""

from dataclasses import dataclass

from crm.media.services.audio_transcription import AudioTranscriptionService
from crm.support.domain.enums import AttachmentType
from crm.support.services.ticket_creator import SupportTicketCreator, TicketCreationResult
from crm.support.services.ticket_lifecycle import TicketLifecycleService


@dataclass(frozen=True)
class AudioTicketResult:
    created: bool
    ticket_id: str | None
    suggested_reply: str = ""
    error: str = ""


class AudioTicketExtractor:
    @staticmethod
    def run(
        *,
        media_asset,
        contact,
        conversation_id=None,
        source_message_id=None,
        transcription=None,
        actor=None,
        request=None,
    ) -> AudioTicketResult:
        from crm.ai.services.ai_gateway import AIGateway
        from crm.organizations.models import Organization

        organization = Organization.objects.get(id=media_asset.organization_id)

        if transcription is None or transcription.status != "completed":
            transcription = AudioTranscriptionService.transcribe(media_asset=media_asset)
        if transcription.status != "completed" or not transcription.text:
            return AudioTicketResult(
                created=False, ticket_id=None, error="transcription_unavailable"
            )

        extraction_result = AIGateway.extract_ticket_from_audio(
            organization_id=organization.id,
            transcription=transcription.text,
            contact=contact,
            references={"contact_id": contact.id, "conversation_id": conversation_id},
        )
        # Invalid/unsafe structured output -> no ticket.
        if not extraction_result.succeeded or not extraction_result.data:
            return AudioTicketResult(
                created=False,
                ticket_id=None,
                error=extraction_result.error_code or "invalid_ai_output",
            )

        result: TicketCreationResult = SupportTicketCreator.create_from_ai_extraction(
            organization=organization,
            contact=contact,
            extraction=extraction_result.data,
            conversation_id=conversation_id,
            source_message_id=source_message_id,
            actor=actor,
            request=request,
        )
        # Attach the source audio to the ticket.
        if result.created:
            TicketLifecycleService.add_attachment(
                ticket=result.ticket,
                media_asset_id=media_asset.id,
                attachment_type=AttachmentType.AUDIO.value,
                source_message_id=source_message_id,
                actor=actor,
                request=request,
            )
        return AudioTicketResult(
            created=result.created,
            ticket_id=str(result.ticket.id),
            suggested_reply=result.suggested_reply,
        )


# Convenience alias matching the spec name.
class TicketFromAudioService:
    run = staticmethod(AudioTicketExtractor.run)
