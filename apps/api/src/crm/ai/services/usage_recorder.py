"""UsageRecorder: persist an AIUsageRecord per run and stamp cost on the run."""

from crm.ai.domain.value_objects import AIUsage
from crm.ai.models import AIRun, AIUsageRecord

from .cost_tracker import CostTracker


class UsageRecorder:
    @staticmethod
    def record(*, run: AIRun, usage: AIUsage) -> AIUsageRecord:
        cost = CostTracker.estimate_cost(model=run.model, usage=usage)
        run.estimated_cost = cost
        return AIUsageRecord.objects.create(
            organization_id=run.organization_id,
            ai_run=run,
            provider=run.provider,
            model=run.model,
            purpose=run.purpose,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=usage.cached_tokens,
            audio_seconds=usage.audio_seconds,
            image_count=usage.image_count,
            estimated_cost=cost,
        )
