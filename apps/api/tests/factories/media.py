import hashlib
import uuid

import factory

from crm.media.domain.enums import MediaSource, MediaStatus
from crm.media.models import MediaAsset, Transcription


class MediaAssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MediaAsset

    organization_id = factory.LazyFunction(uuid.uuid4)
    owner_type = "test"
    file_name = factory.Sequence(lambda n: f"file-{n}.ogg")
    mime_type = "audio/ogg"
    size_bytes = 1024
    storage_key = factory.Sequence(
        lambda n: f"{uuid.uuid4()}/2026/06/12/{uuid.uuid4().hex}_file{n}.ogg"
    )
    checksum = factory.LazyFunction(lambda: hashlib.sha256(b"x").hexdigest())
    source = MediaSource.WHATSAPP
    status = MediaStatus.STORED


class TranscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transcription

    media_asset = factory.SubFactory(MediaAssetFactory)
    organization_id = factory.SelfAttribute("media_asset.organization_id")
    text = "Hola, tengo un problema con el sistema."
    status = "completed"
