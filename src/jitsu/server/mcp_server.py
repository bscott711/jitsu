"""The core MCP server implementation for Jitsu."""

import anyio
import mcp.server.stdio
from mcp import types
from mcp.server import Server
from pydantic import ValidationError

from jitsu.core.compiler import ContextCompiler
from jitsu.core.state import JitsuStateManager
from jitsu.models.core import PhaseReport
from jitsu.providers import (
    ASTProvider,
    DirectoryTreeProvider,
    FileStateProvider,
    PydanticV2Provider,
)
from jitsu.server.ipc import IPCServer

# Initialize the global state manager and compiler for the server
state_manager = JitsuStateManager()
context_compiler = ContextCompiler()

# Initialize the MCP Server
app = Server("jitsu")


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Jitsu tools."""
    return [
        types.Tool(
            name="jitsu_get_next_phase",
            description="Get the next Jitsu phase directive to execute.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="jitsu_report_status",
            description="Report the status of a completed phase.",
            inputSchema={
                "type": "object",
                "properties": {
                    "phase_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["SUCCESS", "FAILED", "STUCK"],
                    },
                    "artifacts_generated": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "agent_notes": {"type": "string"},
                    "verification_output": {"type": "string"},
                },
                "required": ["phase_id", "status"],
            },
        ),
        types.Tool(
            name="jitsu_request_context",
            description="On-demand JIT context request for a specific target and provider.",
            inputSchema={
                "type": "object",
                "properties": {
                    "target_identifier": {
                        "type": "string",
                        "description": "The target to resolve (e.g., file path or Pydantic class).",
                    },
                    "provider_name": {
                        "type": "string",
                        "description": "Provider to use (file_state, pydantic_v2, ast, tree).",
                        "default": "file_state",
                    },
                },
                "required": ["target_identifier"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, object] | None
) -> list[types.TextContent]:
    """Handle tool execution requests from the IDE agent."""
    if name == "jitsu_get_next_phase":
        return await _handle_get_next_phase()
    if name == "jitsu_report_status":
        return _handle_report_status(arguments)
    if name == "jitsu_request_context":
        return await _handle_request_context(arguments)

    msg = f"Unknown tool: {name}"
    raise ValueError(msg)


async def _handle_get_next_phase() -> list[types.TextContent]:
    """Handle the 'get_next_phase' tool request."""
    directive = state_manager.get_next_directive()
    if not directive:
        return [types.TextContent(type="text", text="No pending phases in the queue.")]

    compiled_markdown = await context_compiler.compile_directive(directive)
    return [types.TextContent(type="text", text=compiled_markdown)]


def _handle_report_status(arguments: dict[str, object] | None) -> list[types.TextContent]:
    """Handle the 'report_status' tool request."""
    if not arguments:
        return [types.TextContent(type="text", text="Error: Missing arguments.")]

    try:
        report = PhaseReport.model_validate(arguments)
        state_manager.update_phase_status(report)
        msg = f"Successfully recorded status {report.status} for phase {report.phase_id}."
        return [types.TextContent(type="text", text=msg)]
    except ValidationError as e:
        return [types.TextContent(type="text", text=f"Validation Error: {e!s}")]


async def _handle_request_context(arguments: dict[str, object] | None) -> list[types.TextContent]:
    """Handle the 'request_context' tool request."""
    if not arguments or "target_identifier" not in arguments:
        return [types.TextContent(type="text", text="Error: Missing target_identifier.")]

    target_id = str(arguments["target_identifier"])
    provider_name = str(arguments.get("provider_name", "file_state"))

    providers = {
        "file_state": FileStateProvider,
        "pydantic_v2": PydanticV2Provider,
        "ast": ASTProvider,
        "tree": DirectoryTreeProvider,
        "directory_tree": DirectoryTreeProvider,
    }

    provider_cls = providers.get(provider_name)
    if not provider_cls:
        return [types.TextContent(type="text", text=f"Error: Unknown provider '{provider_name}'.")]

    provider = provider_cls()
    context_data = await provider.resolve(target_id)
    return [types.TextContent(type="text", text=context_data)]


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
