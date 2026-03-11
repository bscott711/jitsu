"""Tool registry for MCP server."""

import inspect
import typing

from mcp import types


class ToolRegistry:
    """Registry for MCP tools and their handlers."""

    def __init__(self) -> None:
        """Initialize the tool registry."""
        self._tools: dict[str, types.Tool] = {}
        self._handlers: dict[str, typing.Callable[..., typing.Any]] = {}

    def register(self, tool: types.Tool, handler: typing.Callable[..., typing.Any]) -> None:
        """Register a tool and its handler."""
        self._tools[tool.name] = tool
        self._handlers[tool.name] = handler

    def get_tools(self) -> list[types.Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    async def execute(
        self, name: str, arguments: dict[str, object] | None
    ) -> list[types.TextContent]:
        """Execute a tool handler by name."""
        handler = self._handlers.get(name)
        if not handler:
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)

        # Determine if the handler expects arguments based on its signature
        sig = inspect.signature(handler)
        has_params = len(sig.parameters) > 0

        if inspect.iscoroutinefunction(handler):
            if has_params:
                result = await handler(arguments)
            else:
                result = await handler()
        elif has_params:
            result = handler(arguments)
        else:
            result = handler()

        return typing.cast("list[types.TextContent]", result)
