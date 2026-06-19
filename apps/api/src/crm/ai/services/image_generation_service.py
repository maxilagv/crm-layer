"""ImageGenerationService: thin semantic wrapper over the gateway."""

from crm.ai.domain.result import AIGatewayResult


class ImageGenerationService:
    @staticmethod
    def generate(
        *, organization_id, image_request: str, actor=None, references: dict | None = None
    ) -> AIGatewayResult:
        from .ai_gateway import AIGateway

        return AIGateway.generate_image(
            organization_id=organization_id,
            image_request=image_request,
            actor=actor,
            references=references,
        )
