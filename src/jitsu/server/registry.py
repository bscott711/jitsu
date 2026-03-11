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

        args = arguments or {}
        if inspect.iscoroutinefunction(handler):
            result = await handler(**args)
        else:
            result = handler(**args)

        return typing.cast("list[types.TextContent]", result)
