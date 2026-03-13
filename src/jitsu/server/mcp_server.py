"""The core MCP server implementation for Jitsu."""

import mcp.server.stdio
from mcp import types
from mcp.server import Server

from jitsu.core.compiler import ContextCompiler
from jitsu.core.state import JitsuStateManager
from jitsu.server.handlers import ToolHandlers
from jitsu.server.registry import ToolRegistry

# Initialize the global state manager and compiler for the server
state_manager = JitsuStateManager()
context_compiler = ContextCompiler()

# Initialize the MCP Server
app = Server("jitsu")


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Jitsu tools."""
    return tool_registry.get_tools()


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, object] | None
) -> list[types.TextContent]:
    """Handle tool execution requests from the IDE agent."""
    return await tool_registry.execute(name, arguments)


tool_registry = ToolRegistry()

# Initialize handlers and register all tools
handlers = ToolHandlers(state_manager, context_compiler, server=app)
handlers.register_all(tool_registry)


async def run_server() -> None:
    """Run the MCP server over stdio."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )
