"""generate_image: dispatches image generation to its dedicated Celery queue.

An image render must never block a commercial reply, so the tool only enqueues
the work and returns the queued task reference.
"""

from crm.ai.domain.enums import AIPurpose, RiskLevel
from crm.core.security.permissions import PermissionCode

from .base import BaseTool, ToolContext, ToolDefinition
from .responses import ok


class GenerateImageTool(BaseTool):
    definition = ToolDefinition(
        name="generate_image",
        version="1",
        description="Genera una imagen promocional (se procesa en cola separada).",
        argument_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["prompt"],
            "properties": {
                "prompt": {"type": "string"},
                "aspect_ratio": {"type": "string", "enum": ["1:1", "16:9", "9:16", "4:3"]},
            },
        },
        permissions_required=(PermissionCode.PROMPTS_MANAGE.value,),
        allowed_purposes=(AIPurpose.SALES_REPLY.value, AIPurpose.IMAGE_GENERATION.value),
        side_effects="Encola task Celery ai.generate_image",
        idempotency_scope=("prompt",),
        audit_event="ai_tool_generate_image",
        risk_level=RiskLevel.LOW.value,
    )

    def execute(self, *, arguments, context: ToolContext) -> dict:
        from crm.ai import tasks as ai_tasks

        async_result = ai_tasks.generate_image.delay(
            organization_id=str(context.organization_id),
            prompt=arguments["prompt"],
            requested_by_run_id=str(context.ai_run.id),
        )
        return ok(queued_task_id=str(async_result.id), queue="image_generation")
