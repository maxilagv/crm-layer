"""ToolRegistry: the only source of executable tools."""

from crm.ai.domain.exceptions import AIToolPermissionDenied

from .base import BaseTool

_REGISTRY: dict[str, BaseTool] = {}


def register_tool(tool: BaseTool) -> BaseTool:
    _REGISTRY[tool.definition.name] = tool
    return tool


def get_tool(name: str) -> BaseTool:
    tool = _REGISTRY.get(name)
    if tool is None:
        raise AIToolPermissionDenied(f"Tool '{name}' is not registered")
    return tool


def tool_exists(name: str) -> bool:
    return name in _REGISTRY


def all_tools() -> list[BaseTool]:
    return list(_REGISTRY.values())


def tools_for_purpose(purpose: str) -> list[BaseTool]:
    return [
        tool
        for tool in _REGISTRY.values()
        if not tool.definition.allowed_purposes or purpose in tool.definition.allowed_purposes
    ]


def clear_registry() -> None:
    """Test helper."""
    _REGISTRY.clear()
