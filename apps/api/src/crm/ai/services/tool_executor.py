"""Service-layer alias: the executor lives in crm.ai.tools.executor."""

from crm.ai.tools.executor import ToolExecutor, validate_arguments

__all__ = ["ToolExecutor", "validate_arguments"]
