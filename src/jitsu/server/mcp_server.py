"""The core MCP server implementation for Jitsu."""

import anyio
import mcp.server.stdio
from mcp import types
from mcp.server import Server

from jitsu.core.compiler import ContextCompiler
from jitsu.core.state import JitsuStateManager
from jitsu.server.handlers import ToolHandlers
from jitsu.server.ipc import IPCServer
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
handlers = ToolHandlers(state_manager, context_compiler)
handlers.register_all(tool_registry)


async def run_server() -> None:
    """Run the MCP server over stdio and the IPC daemon concurrently."""
    ipc_server = IPCServer(state_manager=state_manager)

    async with (
        mcp.server.stdio.stdio_server() as (read_stream, write_stream),
        anyio.create_task_group() as tg,
    ):
        # 1. Start the background TCP listener
        tg.start_soon(ipc_server.serve)

        # 2. Block and run the main MCP server
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )

        # 3. If the IDE disconnects and app.run finishes, cancel the IPC daemon cleanly
        tg.cancel_scope.cancel()
