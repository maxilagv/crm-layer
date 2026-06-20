"""Store an AI-generated image (base64) as a private MediaAsset."""

import base64

from crm.media.domain.enums import MediaSource

from .media_asset_creator import MediaAssetCreator


class GeneratedAssetStorage:
    @staticmethod
    def store_b64_image(
        *,
        organization_id,
        b64_content: str,
        file_name: str,
        mime_type: str = "image/png",
        owner_type: str = "image_generation_request",
        owner_id=None,
        actor=None,
    ):
        content = base64.b64decode(b64_content, validate=True)
        return MediaAssetCreator.create_from_bytes(
            organization_id=organization_id,
            content=content,
            file_name=file_name,
            mime_type=mime_type,
            source=MediaSource.AI_GENERATED,
            owner_type=owner_type,
            owner_id=owner_id,
            actor=actor,
            extra_metadata={"generated": True},
        )
