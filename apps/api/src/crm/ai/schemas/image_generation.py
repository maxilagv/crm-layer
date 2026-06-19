from typing import ClassVar, Literal

from crm.ai.domain.enums import AIPurpose

from .base import AISchema, register_schema


@register_schema(AIPurpose.IMAGE_GENERATION.value)
class ImageGenerationSchema(AISchema):
    prompt: str
    style: str = ""
    aspect_ratio: Literal["1:1", "16:9", "9:16", "4:3"] = "1:1"

    example: ClassVar[dict] = {
        "prompt": "Flyer simple para promo de automatización de WhatsApp, estilo limpio.",
        "style": "minimal",
        "aspect_ratio": "1:1",
    }
