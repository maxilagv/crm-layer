"""Anti-coupling guard: openai/anthropic SDKs only inside crm/ai/providers/."""

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "crm"
ALLOWED = SRC / "ai" / "providers"

_IMPORT_RE = re.compile(
    r"^\s*(from\s+(openai|anthropic)[.\s]|import\s+(openai|anthropic)\b)", re.MULTILINE
)


def test_no_business_module_imports_openai_or_anthropic() -> None:
    violations: list[str] = []
    for path in SRC.rglob("*.py"):
        if ALLOWED in path.parents:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if _IMPORT_RE.search(content):
            violations.append(str(path.relative_to(SRC)))
    assert violations == [], "Direct AI SDK imports outside crm/ai/providers/: " + ", ".join(
        violations
    )
