"""Phase 7 AI pipeline: media download, transcription, ticket-from-audio,
support reply safety and image generation. Every AI call goes through the
AIGateway backed by FakeAIProvider — never a provider directly.
"""

import base64

import pytest

from crm.ai.domain.enums import SafetyDecision
from crm.ai.providers.fake_provider import FakeAIProvider
from crm.ai.services.ai_gateway import AIGateway
from crm.media.domain.enums import MediaSource, MediaStatus
from crm.media.domain.exceptions import TranscriptionNotAudio
from crm.media.models import GeneratedImage, MediaAsset
from crm.media.services.audio_transcription import AudioTranscriptionService
from crm.media.services.generated_asset_storage import GeneratedAssetStorage
from crm.media.services.image_generation import ImageGenerationService
from crm.media.services.media_asset_creator import MediaAssetCreator
from crm.media.services.media_downloader import FetchedMedia, MediaDownloader
from crm.media.services.media_storage import MediaStorageService
from crm.support.models import SupportTicket, SupportTicketAttachment
from crm.support.services.support_reply import SupportReplyService
from crm.support.services.ticket_from_audio import TicketFromAudioService
from tests.factories.ai import setup_ai_organization
from tests.factories.contacts import ContactFactory
from tests.factories.conversations import ConversationFactory, MessageFactory
from tests.factories.organizations import OrganizationFactory
from tests.factories.whatsapp import WhatsAppMediaReferenceFactory

OGG = b"OggS\x00\x02" + b"0" * 64
IMAGE_TYPE = "proposal_cover"
ASPECT = "1:1"


@pytest.fixture(autouse=True)
def _reset_fake():
    FakeAIProvider.reset()
    yield
    FakeAIProvider.reset()


@pytest.fixture(autouse=True)
def _private_media(settings, tmp_path):
    settings.MEDIA_PRIVATE_ROOT = str(tmp_path / "private_media")


@pytest.fixture
def ai_org(db):
    org = OrganizationFactory()
    setup_ai_organization(org)
    return org


def _audio_asset(org):
    return MediaAssetCreator.create_from_bytes(
        organization_id=org.id,
        content=OGG,
        file_name="nota.ogg",
        mime_type="audio/ogg",
        source=MediaSource.WHATSAPP,
    )


# ----------------------------------------------------- whatsapp media download


class _FakeAdapter:
    """Stands in for WhatsAppMediaClientAdapter — no Meta call happens."""

    def __init__(self):
        self.calls = 0

    def fetch(self, external_media_id, *, fallback_name="audio"):
        self.calls += 1
        return FetchedMedia(
            content=OGG, mime_type="audio/ogg", sha256="abc123", file_name="nota.ogg"
        )


@pytest.mark.django_db
def test_audio_message_downloads_media():
    ref = WhatsAppMediaReferenceFactory(media_type="audio")
    adapter = _FakeAdapter()
    asset = MediaDownloader.download_from_whatsapp_reference(
        media_reference_id=ref.id, adapter=adapter
    )
    assert adapter.calls == 1
    assert asset.source == MediaSource.WHATSAPP
    assert asset.status == MediaStatus.STORED
    assert asset.mime_type == "audio/ogg"
    # Stored privately under the org prefix; bytes round-trip.
    assert asset.storage_key.startswith(f"{ref.organization_id}/")
    assert MediaStorageService.open_asset(asset) == OGG
    # The reference is linked back to the asset.
    ref.refresh_from_db()
    assert ref.metadata["media_asset_id"] == str(asset.id)
    assert ref.metadata["media_asset_integration"] == "linked"


@pytest.mark.django_db
def test_audio_download_is_idempotent():
    ref = WhatsAppMediaReferenceFactory(media_type="audio")
    adapter = _FakeAdapter()
    first = MediaDownloader.download_from_whatsapp_reference(
        media_reference_id=ref.id, adapter=adapter
    )
    second = MediaDownloader.download_from_whatsapp_reference(
        media_reference_id=ref.id, adapter=adapter
    )
    assert first.id == second.id
    assert adapter.calls == 1  # second call short-circuits
    assert MediaAsset.objects.filter(owner_id=ref.id).count() == 1


# ------------------------------------------------------------- transcription


@pytest.mark.django_db
def test_audio_transcription_created(ai_org):
    asset = _audio_asset(ai_org)
    transcription = AudioTranscriptionService.transcribe(media_asset=asset)
    assert transcription.status == "completed"
    assert transcription.text
    assert transcription.ai_run_id is not None  # provider call was logged
    asset.refresh_from_db()
    assert asset.status == MediaStatus.PROCESSED


@pytest.mark.django_db
def test_transcription_is_idempotent(ai_org):
    asset = _audio_asset(ai_org)
    first = AudioTranscriptionService.transcribe(media_asset=asset)
    second = AudioTranscriptionService.transcribe(media_asset=asset)
    assert first.id == second.id  # completed transcription reused


@pytest.mark.django_db
def test_transcription_rejects_non_audio(ai_org):
    asset = MediaAssetCreator.create_from_bytes(
        organization_id=ai_org.id,
        content=b"\x89PNG\r\n\x1a\n" + b"0" * 32,
        file_name="x.png",
        mime_type="image/png",
        source=MediaSource.DASHBOARD,
    )
    with pytest.raises(TranscriptionNotAudio):
        AudioTranscriptionService.transcribe(media_asset=asset)


# --------------------------------------------------------- ticket from audio


@pytest.mark.django_db
def test_ticket_from_audio_created(ai_org):
    contact = ContactFactory(organization_id=ai_org.id)
    asset = _audio_asset(ai_org)
    result = TicketFromAudioService.run(media_asset=asset, contact=contact)
    assert result.created is True
    ticket = SupportTicket.objects.get(id=result.ticket_id)
    # Built from the validated structured extraction (example output).
    assert ticket.title
    assert ticket.contact_id == contact.id
    # The source audio is attached to the ticket.
    assert SupportTicketAttachment.objects.filter(ticket=ticket, media_asset=asset).exists()


@pytest.mark.django_db
def test_invalid_ai_ticket_output_does_not_create_ticket(ai_org, monkeypatch):
    contact = ContactFactory(organization_id=ai_org.id)
    asset = _audio_asset(ai_org)

    class _Failed:
        succeeded = False
        data = None
        error_code = "invalid_schema"
        error_message = "schema"

    # Force the extraction to fail validation: no ticket may be created.
    monkeypatch.setattr(
        AIGateway, "extract_ticket_from_audio", staticmethod(lambda **kw: _Failed())
    )
    result = TicketFromAudioService.run(media_asset=asset, contact=contact)
    assert result.created is False
    assert SupportTicket.objects.filter(contact=contact).count() == 0


# ----------------------------------------------------------- support reply


@pytest.mark.django_db
def test_support_agent_does_not_request_password(ai_org):
    contact = ContactFactory(organization_id=ai_org.id)
    conversation = ConversationFactory(organization_id=ai_org.id, contact=contact)
    message = MessageFactory(conversation=conversation, body="No puedo entrar a mi cuenta")

    # The model tries to ask for a password; SafetyGuard must block it.
    FakeAIProvider.script(
        {
            "json": {
                "reply": "Para ayudarte necesito que me pases tu contraseña.",
                "intent": "collect_information",
                "confidence": 0.9,
            }
        }
    )
    result = SupportReplyService.generate(conversation_id=conversation.id, message_id=message.id)
    assert result.can_send is False
    assert result.decision in (
        SafetyDecision.DO_NOT_REPLY.value,
        SafetyDecision.HANDOFF_TO_HUMAN.value,
    )


@pytest.mark.django_db
def test_support_reply_safe_message_can_send(ai_org):
    contact = ContactFactory(organization_id=ai_org.id)
    conversation = ConversationFactory(organization_id=ai_org.id, contact=contact)
    message = MessageFactory(conversation=conversation, body="No me carga el panel")
    result = SupportReplyService.generate(conversation_id=conversation.id, message_id=message.id)
    assert result.reply
    assert result.can_send is True


# --------------------------------------------------------- image generation


@pytest.mark.django_db
def test_generated_image_is_stored(ai_org):
    image_request = ImageGenerationService.request_generation(
        organization_id=ai_org.id,
        prompt="Una portada para una propuesta comercial",
        image_type=IMAGE_TYPE,
        aspect_ratio=ASPECT,
        dispatch=False,
    )
    image_request = ImageGenerationService.run_generation(image_request.id)
    assert image_request.status == "completed"
    asset = image_request.result_media_asset
    assert asset is not None
    assert asset.source == MediaSource.AI_GENERATED
    assert asset.status == MediaStatus.STORED
    # Private storage, retrievable, decoded from the provider's base64.
    assert asset.storage_key.startswith(f"{ai_org.id}/")
    assert MediaStorageService.open_asset(asset) == base64.b64decode("ZmFrZS1pbWFnZS1ieXRlcw==")
    assert GeneratedImage.objects.filter(image_generation_request=image_request).count() == 1


@pytest.mark.django_db
def test_generated_asset_storage_is_private(ai_org):
    asset = GeneratedAssetStorage.store_b64_image(
        organization_id=ai_org.id,
        b64_content="ZmFrZS1pbWFnZS1ieXRlcw==",
        file_name="cover.png",
    )
    assert asset.source == MediaSource.AI_GENERATED
    assert asset.storage_provider == "local"
    assert asset.storage_key.startswith(f"{ai_org.id}/")
