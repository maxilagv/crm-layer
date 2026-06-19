"""Tool framework + built-in tool registration."""

from .base import BaseTool, ToolContext, ToolDefinition
from .executor import ToolExecutor
from .registry import all_tools, get_tool, register_tool, tool_exists, tools_for_purpose

_registered = False


def register_builtin_tools() -> None:
    """Idempotent registration of the built-in tools (called from AppConfig.ready)."""
    global _registered
    if _registered:
        return
    from .create_call_request import CreateCallRequestTool
    from .create_task import CreateTaskTool
    from .create_ticket import CreateTicketTool
    from .generate_image import GenerateImageTool
    from .notify_owner import NotifyOwnerTool
    from .pause_conversation_ai import PauseConversationAITool
    from .send_whatsapp_message import SendWhatsAppMessageTool
    from .update_lead import UpdateLeadTool

    for tool_class in (
        CreateTaskTool,
        UpdateLeadTool,
        CreateTicketTool,
        NotifyOwnerTool,
        SendWhatsAppMessageTool,
        PauseConversationAITool,
        CreateCallRequestTool,
        GenerateImageTool,
    ):
        register_tool(tool_class())
    _registered = True


__all__ = [
    "BaseTool",
    "ToolContext",
    "ToolDefinition",
    "ToolExecutor",
    "all_tools",
    "get_tool",
    "register_builtin_tools",
    "register_tool",
    "tool_exists",
    "tools_for_purpose",
]
