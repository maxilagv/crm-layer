"""Service-layer alias: the registry lives in crm.ai.tools.registry."""

from crm.ai.tools.registry import all_tools, get_tool, register_tool, tools_for_purpose

__all__ = ["all_tools", "get_tool", "register_tool", "tools_for_purpose"]
