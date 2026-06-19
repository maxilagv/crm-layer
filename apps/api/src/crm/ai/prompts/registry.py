"""PromptRegistry: DB-backed prompt resolution + version lifecycle.

Rules enforced here:
- only one ACTIVE version per prompt;
- activating a version archives the previous active one;
- an active version is immutable (changes require a new draft);
- every activation is audited.
"""

from django.db import transaction
from django.utils import timezone

from crm.ai.domain.enums import PromptStatus
from crm.ai.domain.exceptions import AIPromptMissing
from crm.ai.models import AIPrompt, AIPromptVersion
from crm.audit.services import audit_event_create

from .validators import PromptValidator


class PromptRegistry:
    @staticmethod
    def get_active_version(*, organization_id, key: str) -> AIPromptVersion:
        prompt = (
            AIPrompt.objects.filter(organization_id=organization_id, key=key)
            .select_related("active_version")
            .first()
        )
        if prompt is None:
            raise AIPromptMissing(f"Prompt '{key}' not found for organization")
        if prompt.active_version is None:
            raise AIPromptMissing(f"Prompt '{key}' has no active version")
        return prompt.active_version

    @staticmethod
    @transaction.atomic
    def create_draft(
        *,
        prompt: AIPrompt,
        system_prompt: str,
        developer_prompt: str = "",
        template: str = "",
        output_schema: dict | None = None,
        examples: list | None = None,
        change_notes: str = "",
        created_by=None,
    ) -> AIPromptVersion:
        last = prompt.versions.order_by("-version").first()
        next_number = (last.version + 1) if last else 1
        return AIPromptVersion.objects.create(
            organization_id=prompt.organization_id,
            prompt=prompt,
            version=next_number,
            status=PromptStatus.DRAFT,
            system_prompt=system_prompt,
            developer_prompt=developer_prompt,
            template=template,
            output_schema=output_schema,
            examples=examples or [],
            change_notes=change_notes,
            created_by_id=getattr(created_by, "id", None),
        )

    @staticmethod
    @transaction.atomic
    def activate_version(*, version: AIPromptVersion, actor=None, request=None) -> AIPromptVersion:
        PromptValidator.assert_activatable(version)
        prompt = AIPrompt.objects.select_for_update().get(id=version.prompt_id)
        now = timezone.now()

        previous = prompt.active_version
        if previous is not None and previous.id != version.id:
            previous.status = PromptStatus.ARCHIVED
            previous.archived_at = now
            previous.save(update_fields=["status", "archived_at", "updated_at"])

        version.status = PromptStatus.ACTIVE
        version.activated_at = now
        version.archived_at = None
        version.save(update_fields=["status", "activated_at", "archived_at", "updated_at"])

        prompt.active_version = version
        prompt.save(update_fields=["active_version", "updated_at"])

        audit_event_create(
            event_type="ai_prompt_version_activated",
            actor=actor,
            organization=_org_stub(prompt.organization_id),
            request=request,
            resource_type="ai_prompt_version",
            resource_id=str(version.id),
            metadata={
                "prompt_key": prompt.key,
                "version": version.version,
                "previous_version": previous.version if previous else None,
            },
        )
        return version

    @staticmethod
    @transaction.atomic
    def archive_version(*, version: AIPromptVersion, actor=None, request=None) -> AIPromptVersion:
        prompt = AIPrompt.objects.select_for_update().get(id=version.prompt_id)
        version.status = PromptStatus.ARCHIVED
        version.archived_at = timezone.now()
        version.save(update_fields=["status", "archived_at", "updated_at"])
        if prompt.active_version_id == version.id:
            prompt.active_version = None
            prompt.save(update_fields=["active_version", "updated_at"])
        audit_event_create(
            event_type="ai_prompt_version_archived",
            actor=actor,
            organization=_org_stub(prompt.organization_id),
            request=request,
            resource_type="ai_prompt_version",
            resource_id=str(version.id),
            metadata={"prompt_key": prompt.key, "version": version.version},
        )
        return version


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()
