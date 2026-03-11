"""Tests for the ToolRegistry."""

import pytest
from mcp import types

from jitsu.server.registry import ToolRegistry


@pytest.mark.asyncio
async def test_tool_registry_register_and_get() -> None:
    """Test that tools can be registered and retrieved."""
    registry = ToolRegistry()
    tool = types.Tool(
        name="test_tool",
        description="A test tool",
        inputSchema={"type": "object", "properties": {}},
    )

    def handler() -> list[types.TextContent]:
        return [types.TextContent(type="text", text="success")]

    registry.register(tool, handler)
    tools = registry.get_tools()

    assert len(tools) == 1
    assert tools[0].name == "test_tool"


@pytest.mark.asyncio
async def test_tool_registry_execute_sync_no_args() -> None:
    """Test executing a synchronous handler with no arguments."""
    registry = ToolRegistry()
    tool = types.Tool(
        name="test_tool",
        description="A test tool",
        inputSchema={"type": "object", "properties": {}},
    )

    def handler() -> list[types.TextContent]:
        return [types.TextContent(type="text", text="sync success")]

    registry.register(tool, handler)
    result = await registry.execute("test_tool", {})

    assert len(result) == 1
    assert result[0].text == "sync success"


@pytest.mark.asyncio
async def test_tool_registry_execute_sync_with_args() -> None:
    """Test executing a synchronous handler with arguments."""
    registry = ToolRegistry()
    tool = types.Tool(
        name="test_tool",
        description="A test tool",
        inputSchema={"type": "object", "properties": {"val": {"type": "string"}}},
    )

    def handler(arguments: dict[str, object] | None) -> list[types.TextContent]:
        val = str(arguments["val"]) if arguments else "missing"
        return [types.TextContent(type="text", text=val)]

    registry.register(tool, handler)
    result = await registry.execute("test_tool", {"val": "hello"})

    assert len(result) == 1
    assert result[0].text == "hello"


@pytest.mark.asyncio
async def test_tool_registry_execute_async_no_args() -> None:
    """Test executing an asynchronous handler with no arguments."""
    registry = ToolRegistry()
    tool = types.Tool(
        name="test_tool",
        description="A test tool",
        inputSchema={"type": "object", "properties": {}},
    )

    async def handler() -> list[types.TextContent]:
        return [types.TextContent(type="text", text="async success")]

    registry.register(tool, handler)
    result = await registry.execute("test_tool", {})

    assert len(result) == 1
    assert result[0].text == "async success"


@pytest.mark.asyncio
async def test_tool_registry_execute_async_with_args() -> None:
    """Test executing an asynchronous handler with arguments."""
    registry = ToolRegistry()
    tool = types.Tool(
        name="test_tool",
        description="A test tool",
        inputSchema={"type": "object", "properties": {"val": {"type": "string"}}},
    )

    async def handler(arguments: dict[str, object] | None) -> list[types.TextContent]:
        val = str(arguments["val"]) if arguments else "missing"
        return [types.TextContent(type="text", text=val)]

    registry.register(tool, handler)
    result = await registry.execute("test_tool", {"val": "hello"})

    assert len(result) == 1
    assert result[0].text == "hello"


@pytest.mark.asyncio
async def test_tool_registry_execute_unknown_tool() -> None:
    """Test that executing an unknown tool raises ValueError."""
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="Unknown tool: missing"):
        await registry.execute("missing", {})
