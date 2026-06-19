"""PromptRenderer: safe template rendering with required-variable validation.

Templates use ``{variable}`` placeholders restricted to identifiers. Rendering
fails fast if any placeholder is missing — incomplete prompts never reach a
provider. Values are stringified; dicts/lists are JSON-encoded so structured
context is injected safely (no eval, no format-spec tricks).
"""

import json
import re
from typing import Any

from crm.ai.domain.exceptions import AIPromptRenderError
from crm.ai.domain.value_objects import RenderedPrompt

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def placeholders_in(template: str) -> set[str]:
    return set(_PLACEHOLDER_RE.findall(template or ""))


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def render_template(template: str, variables: dict[str, Any]) -> str:
    required = placeholders_in(template)
    missing = sorted(required - set(variables))
    if missing:
        raise AIPromptRenderError(f"Missing required prompt variables: {', '.join(missing)}")

    def replace(match: re.Match) -> str:
        return _stringify(variables[match.group(1)])

    return _PLACEHOLDER_RE.sub(replace, template or "")


class PromptRenderer:
    @staticmethod
    def render(prompt_version, variables: dict[str, Any]) -> RenderedPrompt:
        """Render system/developer/template of an AIPromptVersion."""
        return RenderedPrompt(
            system_prompt=render_template(prompt_version.system_prompt, variables),
            developer_prompt=render_template(prompt_version.developer_prompt, variables),
            user_content=render_template(prompt_version.template, variables),
            prompt_version_id=prompt_version.id,
            output_schema=prompt_version.output_schema,
            variables_used={key: variables[key] for key in sorted(variables)},
        )
