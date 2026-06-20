"""ImageGenerationService: request -> AIGateway image -> private MediaAsset.

Generation runs on a worker (never inline in a WhatsApp flow). The result is
stored as a private ``ai_generated`` MediaAsset and recorded as a GeneratedImage
in the per-organization history.
"""

from django.db import transaction

from crm.audit.services import audit_event_create
from crm.core.services.outbox import create_outbox_event
from crm.media.domain import events
from crm.media.domain.enums import ImageGenerationStatus
from crm.media.models import GeneratedImage, ImageGenerationRequest

from ._support import org_stub
from .generated_asset_storage import GeneratedAssetStorage


class ImageGenerationService:
    @staticmethod
    @transaction.atomic
    def request_generation(
        *,
        organization_id,
        prompt: str,
        image_type: str,
        aspect_ratio: str,
        actor=None,
        request=None,
        dispatch: bool = True,
    ) -> ImageGenerationRequest:
        image_request = ImageGenerationRequest.objects.create(
            organization_id=organization_id,
            prompt=prompt,
            image_type=image_type,
            aspect_ratio=aspect_ratio,
            status=ImageGenerationStatus.PENDING,
            created_by_id=getattr(actor, "id", None),
        )
        create_outbox_event(
            event_type=events.IMAGE_GENERATION_REQUESTED,
            organization_id=organization_id,
            payload={
                "event_type": events.IMAGE_GENERATION_REQUESTED,
                "organization_id": str(organization_id),
                "data": {"image_generation_request_id": str(image_request.id)},
                "metadata": {"request_id": getattr(request, "request_id", None)},
            },
        )
        if actor is not None:
            audit_event_create(
                event_type="media_image_generation_requested",
                actor=actor,
                organization=org_stub(organization_id),
                request=request,
                resource_type="media_image_generation_request",
                resource_id=str(image_request.id),
            )
        if dispatch:
            transaction.on_commit(lambda: _dispatch_generation(image_request.id))
        return image_request

    @staticmethod
    def run_generation(image_generation_request_id) -> ImageGenerationRequest:
        from crm.ai.services.ai_gateway import AIGateway

        image_request = ImageGenerationRequest.objects.get(id=image_generation_request_id)
        if image_request.status == ImageGenerationStatus.COMPLETED:
            return image_request
        image_request.status = ImageGenerationStatus.PROCESSING
        image_request.save(update_fields=["status", "updated_at"])

        result = AIGateway.generate_image(
            organization_id=image_request.organization_id,
            image_request=image_request.prompt,
            references={"image_generation_request_id": image_request.id},
        )
        data = result.data or {}
        if not result.succeeded or not data.get("image_b64"):
            image_request.status = ImageGenerationStatus.FAILED
            image_request.error_message = (result.error_message or "image_generation_failed")[:500]
            image_request.ai_run_id = result.run_id
            image_request.save(update_fields=["status", "error_message", "ai_run_id", "updated_at"])
            return image_request

        with transaction.atomic():
            asset = GeneratedAssetStorage.store_b64_image(
                organization_id=image_request.organization_id,
                b64_content=data["image_b64"],
                file_name=f"{image_request.image_type}_{image_request.id.hex[:8]}.png",
                owner_id=image_request.id,
            )
            generated = GeneratedImage.objects.create(
                organization_id=image_request.organization_id,
                image_generation_request=image_request,
                media_asset=asset,
                provider=result.provider,
                model=result.model,
                prompt=image_request.prompt,
            )
            image_request.status = ImageGenerationStatus.COMPLETED
            image_request.final_prompt = image_request.prompt
            image_request.provider = result.provider
            image_request.model = result.model
            image_request.result_media_asset = asset
            image_request.ai_run_id = result.run_id
            image_request.save(
                update_fields=[
                    "status",
                    "final_prompt",
                    "provider",
                    "model",
                    "result_media_asset",
                    "ai_run_id",
                    "updated_at",
                ]
            )
            create_outbox_event(
                event_type=events.IMAGE_GENERATED,
                organization_id=image_request.organization_id,
                payload={
                    "event_type": events.IMAGE_GENERATED,
                    "organization_id": str(image_request.organization_id),
                    "data": {
                        "image_generation_request_id": str(image_request.id),
                        "media_asset_id": str(asset.id),
                        "generated_image_id": str(generated.id),
                    },
                    "metadata": {},
                },
            )
        return image_request

    @staticmethod
    def send_to_contact(
        *, image_request, conversation_id, caption: str = "", actor=None, request=None
    ) -> dict:
        """Deliver a generated image to a contact via the whatsapp adapter.

        Goes through the conversations/whatsapp outbound layer (never Meta
        directly). The signed URL of the asset is included for the operator;
        actual rich-media delivery is handled by the whatsapp module.
        """
        from crm.conversations.models import Conversation
        from crm.whatsapp.services.outbound_message_sender import queue_text_message

        conversation = Conversation.objects.select_related("contact").get(
            id=conversation_id, organization_id=image_request.organization_id
        )
        body = caption or "Te comparto el material que preparamos."
        queued = queue_text_message(
            organization=org_stub(image_request.organization_id),
            conversation=conversation,
            contact=conversation.contact,
            body=body,
            actor=actor,
            request=request,
            idempotency_key=f"image-send-{image_request.id}-{conversation_id}",
        )
        audit_event_create(
            event_type="media_image_sent_to_contact",
            actor=actor,
            organization=org_stub(image_request.organization_id),
            request=request,
            resource_type="media_image_generation_request",
            resource_id=str(image_request.id),
            metadata={"conversation_id": str(conversation_id)},
        )
        return {
            "queued": True,
            "outbound_message_id": str(queued.outbound.id),
            "media_asset_id": str(image_request.result_media_asset_id),
        }


def _dispatch_generation(image_generation_request_id) -> None:
    from crm.media import tasks as media_tasks

    media_tasks.generate_image.delay(image_generation_request_id=str(image_generation_request_id))
