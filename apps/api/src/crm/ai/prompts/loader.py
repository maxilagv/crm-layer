"""PromptLoader: seed/update DB prompts from the versioned folders in this package.

Each subfolder ships ``system.md``, ``developer.md``, ``schema.json``,
``examples.yaml`` and ``README.md``.

- ``seed_organization`` is idempotent: missing prompt keys are created with v1
  active; existing keys are left untouched (their lifecycle is owned by the DB).
- ``update_organization`` adopts repo changes into an existing org: for each
  prompt whose active content differs from the files, it creates a NEW draft and
  (by default) activates it — the previous version is archived, never lost.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import yaml
from django.db import transaction

from crm.ai.domain.enums import AIPurpose
from crm.ai.models import AIPrompt

from .registry import PromptRegistry

PROMPTS_DIR = Path(__file__).resolve().parent

# folder name -> (prompt key, purpose)
PROMPT_FOLDERS: dict[str, tuple[str, str]] = {
    "sales_agent": ("sales_agent_v1", AIPurpose.SALES_REPLY.value),
    "support_agent": ("support_agent_v1", AIPurpose.SUPPORT_REPLY.value),
    "assistant_agent": ("assistant_agent_v1", AIPurpose.ASSISTANT_REPLY.value),
    "lead_scoring": ("lead_scoring_v1", AIPurpose.LEAD_SCORING.value),
    "task_extraction": ("task_extraction_v1", AIPurpose.TASK_EXTRACTION.value),
    "audio_ticket_extraction": (
        "audio_ticket_extraction_v1",
        AIPurpose.AUDIO_TICKET_EXTRACTION.value,
    ),
    "conversation_summary": ("conversation_summary_v1", AIPurpose.CONVERSATION_SUMMARY.value),
    "risk_classifier": ("risk_classifier_v1", AIPurpose.RISK_CLASSIFICATION.value),
    "image_generation": ("image_generation_v1", AIPurpose.IMAGE_GENERATION.value),
    "document_draft": ("document_draft_v1", AIPurpose.DOCUMENT_DRAFT.value),
    "memory_extraction": ("memory_extraction_v1", AIPurpose.MEMORY_EXTRACTION.value),
    "project_brief": ("project_brief_v1", AIPurpose.PROJECT_BRIEF.value),
    "prospect_qualification": (
        "prospect_qualification_v1",
        AIPurpose.PROSPECT_QUALIFICATION.value,
    ),
    "outreach_opener": ("outreach_opener_v1", AIPurpose.OUTREACH_OPENER.value),
    "outreach_reply": ("outreach_reply_v1", AIPurpose.OUTREACH_REPLY.value),
    "reply_intent": ("reply_intent_v1", AIPurpose.REPLY_INTENT.value),
}


@dataclass(frozen=True)
class PromptDefinition:
    key: str
    purpose: str
    system_prompt: str
    developer_prompt: str
    template: str
    output_schema: dict | None
    examples: list


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_definition(folder_name: str) -> PromptDefinition:
    key, purpose = PROMPT_FOLDERS[folder_name]
    folder = PROMPTS_DIR / folder_name
    schema_path = folder / "schema.json"
    examples_path = folder / "examples.yaml"
    schema = json.loads(schema_path.read_text(encoding="utf-8")) if schema_path.exists() else None
    examples_raw = (
        yaml.safe_load(examples_path.read_text(encoding="utf-8")) if examples_path.exists() else []
    )
    examples = examples_raw if isinstance(examples_raw, list) else []
    system = _read(folder / "system.md")
    # By convention the template (user content) lives at the end of developer.md
    # under a "## Template" heading; otherwise developer.md is all developer text.
    developer = _read(folder / "developer.md")
    template = ""
    marker = "## Template\n"
    if marker in developer:
        developer, _, template = developer.partition(marker)
    return PromptDefinition(
        key=key,
        purpose=purpose,
        system_prompt=system.strip(),
        developer_prompt=developer.strip(),
        template=template.strip(),
        output_schema=schema,
        examples=examples,
    )


def _matches(version, definition: PromptDefinition) -> bool:
    return (
        version.system_prompt == definition.system_prompt
        and version.developer_prompt == definition.developer_prompt
        and version.template == definition.template
        and (version.output_schema or None) == (definition.output_schema or None)
        and (version.examples or []) == (definition.examples or [])
    )


def _create_prompt(organization_id, definition: PromptDefinition, actor=None) -> AIPrompt:
    prompt = AIPrompt.objects.create(
        organization_id=organization_id,
        key=definition.key,
        name=definition.key.replace("_", " ").title(),
        description=f"Prompt inicial para {definition.purpose}",
        purpose=definition.purpose,
    )
    version = PromptRegistry.create_draft(
        prompt=prompt,
        system_prompt=definition.system_prompt,
        developer_prompt=definition.developer_prompt,
        template=definition.template,
        output_schema=definition.output_schema,
        examples=definition.examples,
        change_notes="Versión inicial cargada desde el repositorio",
        created_by=actor,
    )
    PromptRegistry.activate_version(version=version, actor=actor)
    return prompt


class PromptLoader:
    @staticmethod
    @transaction.atomic
    def seed_organization(organization_id, *, actor=None) -> list[str]:
        """Create missing prompts (with v1 active) for an organization. Idempotent."""
        created: list[str] = []
        for folder_name in PROMPT_FOLDERS:
            definition = load_definition(folder_name)
            if AIPrompt.objects.filter(
                organization_id=organization_id, key=definition.key
            ).exists():
                continue
            _create_prompt(organization_id, definition, actor)
            created.append(definition.key)
        return created

    @staticmethod
    @transaction.atomic
    def update_organization(organization_id, *, activate: bool = True, actor=None) -> list[str]:
        """Adopt repo prompt changes: new draft (optionally activated) where content differs.

        Creates the prompt if it does not exist yet. Returns the keys touched.
        """
        touched: list[str] = []
        for folder_name in PROMPT_FOLDERS:
            definition = load_definition(folder_name)
            prompt = (
                AIPrompt.objects.filter(organization_id=organization_id, key=definition.key)
                .select_related("active_version")
                .first()
            )
            if prompt is None:
                _create_prompt(organization_id, definition, actor)
                touched.append(f"{definition.key} (nuevo)")
                continue
            active = prompt.active_version
            if active is not None and _matches(active, definition):
                continue
            version = PromptRegistry.create_draft(
                prompt=prompt,
                system_prompt=definition.system_prompt,
                developer_prompt=definition.developer_prompt,
                template=definition.template,
                output_schema=definition.output_schema,
                examples=definition.examples,
                change_notes="Actualización cargada desde el repositorio",
                created_by=actor,
            )
            if activate:
                PromptRegistry.activate_version(version=version, actor=actor)
            touched.append(f"{definition.key} (v{version.version}{'' if activate else ' draft'})")
        return touched
