"""The core MCP server implementation for Jitsu."""

import json

import mcp.server.stdio
from mcp import types
from mcp.server import Server

from jitsu.core.compiler import ContextCompiler
from jitsu.core.state import JitsuStateManager
from jitsu.models.core import AgentDirective
from jitsu.server.handlers import ToolHandlers
from jitsu.server.registry import ToolRegistry

# Initialize the global state manager and compiler for the server
state_manager = JitsuStateManager()
context_compiler = ContextCompiler()

# Initialize the MCP Server
app = Server("jitsu")

# ✅ Define tool_registry BEFORE using it in decorators
tool_registry = ToolRegistry()

# Initialize handlers and register all tools
handlers = ToolHandlers(state_manager, context_compiler, server=app)
handlers.register_all(tool_registry)


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Jitsu tools."""
    return tool_registry.get_tools()  # ✅ Now works


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, object] | None
) -> list[types.TextContent]:
    """Handle tool execution requests from the IDE agent."""
    return await tool_registry.execute(name, arguments)


async def handle_agent_plan(arguments: dict[str, object] | None) -> list[types.TextContent]:
    """Handle the 'jitsu_agent_plan' tool request."""
    if not arguments or "objective" not in arguments:
        return [types.TextContent(type="text", text="Error: Missing 'objective' argument.")]

    objective = str(arguments["objective"])
    schema_json = json.dumps(AgentDirective.model_json_schema(), indent=2)

    msg = (
        f"Use `jitsu / plan_epic` to plan this objective: {objective}. "
        f"You must generate a JSON array of AgentDirectives strictly matching this schema: {schema_json}. "
        f"Write the resulting JSON directly to .jitsu/epics/ using your file-writing capabilities. "
        f"Do not execute the epic yet."
    )
    return [types.TextContent(type="text", text=msg)]


# Register the legacy agent plan tool
tool_registry.register(
    types.Tool(
        name="jitsu_agent_plan",
        description="Plan a new epic using the agent's native reasoning.",
        inputSchema={
            "type": "object",
            "properties": {
                "objective": {
                    "type": "string",
                    "description": "The high-level objective for the new epic.",
                },
            },
            "required": ["objective"],
        },
    ),
    handle_agent_plan,
)


async def run_server() -> None:
    """Run the MCP server over stdio."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )
