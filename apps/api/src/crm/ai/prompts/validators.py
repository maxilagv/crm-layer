"""PromptValidator: structural checks before a version can be activated."""

from crm.ai.domain.enums import PURPOSES_REQUIRING_SCHEMA
from crm.ai.domain.exceptions import AIPromptRenderError

from .renderer import placeholders_in


class PromptValidator:
    @staticmethod
    def validate_version(prompt_version) -> list[str]:
        """Return a list of problems; empty list means the version is activatable."""
        problems: list[str] = []
        if not (prompt_version.system_prompt or "").strip():
            problems.append("system_prompt is empty")
        purpose = prompt_version.prompt.purpose
        if (
            purpose in {p.value for p in PURPOSES_REQUIRING_SCHEMA}
            and not prompt_version.output_schema
        ):
            problems.append(f"purpose '{purpose}' mutates data and requires output_schema")
        # Placeholders must be well-formed identifiers (regex enforces it); an
        # unbalanced brace renders literally, so check for obvious mistakes.
        for field in ("system_prompt", "developer_prompt", "template"):
            text = getattr(prompt_version, field) or ""
            if text.count("{") != text.count("}"):
                problems.append(f"{field} has unbalanced braces")
        return problems

    @staticmethod
    def assert_activatable(prompt_version) -> None:
        problems = PromptValidator.validate_version(prompt_version)
        if problems:
            raise AIPromptRenderError("Prompt version not activatable: " + "; ".join(problems))

    @staticmethod
    def required_variables(prompt_version) -> set[str]:
        return (
            placeholders_in(prompt_version.system_prompt)
            | placeholders_in(prompt_version.developer_prompt)
            | placeholders_in(prompt_version.template)
        )
