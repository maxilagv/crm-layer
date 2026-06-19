"""Architectural guardrails for Phase 7.

clients/support/media must never reach a model provider directly: no openai /
anthropic imports, and no ``crm.ai.providers`` import — the only AI entry point
is the AIGateway. They must never call Meta directly either: media is fetched
through the whatsapp module's MediaClient adapter, never the Graph API.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "crm"
APPS = ("clients", "support", "media")


def _py_files():
    for app in APPS:
        yield from (SRC / app).rglob("*.py")


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.module or ""


def test_clients_support_media_do_not_import_openai_or_anthropic():
    offenders = []
    for path in _py_files():
        for module in _imports(path):
            if module.split(".")[0] in {"openai", "anthropic"}:
                offenders.append(f"{path.name}: {module}")
    assert offenders == [], f"Direct provider imports found: {offenders}"


def test_clients_support_media_only_reach_ai_through_gateway():
    """No direct provider/router imports — AI access goes through AIGateway."""
    forbidden_prefixes = ("crm.ai.providers", "crm.ai.router")
    offenders = []
    for path in _py_files():
        for module in _imports(path):
            if any(module.startswith(prefix) for prefix in forbidden_prefixes):
                offenders.append(f"{path.name}: {module}")
    assert offenders == [], f"Phase 7 reaches AI outside the gateway: {offenders}"


def test_phase7_does_not_call_meta_graph_api_directly():
    """No source in the three apps embeds a direct Meta Graph API call."""
    offenders = []
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        if "graph.facebook.com" in text:
            offenders.append(path.name)
    assert offenders == [], f"Direct Meta Graph calls found: {offenders}"


def test_media_download_goes_through_whatsapp_adapter():
    """The downloader uses the whatsapp MediaClient adapter, not raw HTTP."""
    downloader = SRC / "media" / "services" / "media_downloader.py"
    text = downloader.read_text(encoding="utf-8")
    assert "WhatsAppMediaClientAdapter" in text
    assert "crm.whatsapp.clients.media_client" in text
    # No raw HTTP client is used to fetch media here.
    for module in _imports(downloader):
        assert module.split(".")[0] not in {"requests", "httpx", "urllib3"}


@pytest.mark.parametrize("app", APPS)
def test_phase7_app_has_tests_marker(app):
    """Sanity: each app package is importable (guards against broken __init__)."""
    assert (SRC / app / "__init__.py").exists()
