"""The core MCP server implementation for Jitsu."""

import mcp.server.stdio
from mcp import types
from mcp.server import Server
from pydantic import ValidationError

from jitsu.core.state import JitsuStateManager
from jitsu.models.core import PhaseReport

# Initialize the global state manager for the server
state_manager = JitsuStateManager()

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
                },
                "required": ["phase_id", "status"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, object] | None
) -> list[types.TextContent]:
    """Handle tool execution requests from the IDE agent."""
    if name == "jitsu_get_next_phase":
        directive = state_manager.get_next_directive()
        if not directive:
            return [types.TextContent(type="text", text="No pending phases in the queue.")]

        return [types.TextContent(type="text", text=directive.model_dump_json(indent=2))]

    if name == "jitsu_report_status":
        if not arguments:
            return [types.TextContent(type="text", text="Error: Missing arguments.")]

        try:
            report = PhaseReport.model_validate(arguments)
            state_manager.update_phase_status(report)

            # CHANGE: Removed .value since report.status is already a string
            msg = f"Successfully recorded status {report.status} for phase {report.phase_id}."
            return [types.TextContent(type="text", text=msg)]

        except ValidationError as e:
            err_msg = f"Validation Error: {e!s}"
            return [types.TextContent(type="text", text=err_msg)]

    msg = f"Unknown tool: {name}"
    raise ValueError(msg)


async def run_server() -> None:
    """Run the MCP server over stdio."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )  # pragma: no cover
