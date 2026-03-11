"""The core MCP server implementation for Jitsu."""

import re
import subprocess
import typing
from pathlib import Path

import anyio
import mcp.server.stdio
from mcp import types
from mcp.server import Server
from pydantic import ValidationError

from jitsu.core.compiler import ContextCompiler
from jitsu.core.state import JitsuStateManager
from jitsu.models.core import AgentDirective, PhaseReport, PhaseStatus
from jitsu.providers import DirectoryTreeProvider, GitProvider, ProviderRegistry
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
                        "description": "Provider to use (file, pydantic, ast, tree).",
                        "default": "file",
                    },
                },
                "required": ["target_identifier"],
            },
        ),
        types.Tool(
            name="jitsu_get_planning_context",
            description="Get the repository skeleton and .jitsurules to help plan an epic.",
            inputSchema={
                "type": "object",
                "properties": {
                    "relevant_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of files relevant to the planning task.",
                    }
                },
            },
        ),
        types.Tool(
            name="jitsu_submit_epic",
            description="Submit an array of phase directives to the Jitsu queue.",
            inputSchema={
                "type": "object",
                "properties": {
                    "directives": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "An array of validated AgentDirective objects.",
                    }
                },
                "required": ["directives"],
            },
        ),
        types.Tool(
            name="jitsu_inspect_queue",
            description="Inspect the current queue of pending phases.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="jitsu_git_status",
            description="Returns the output of 'git status --short'.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="jitsu_git_commit",
            description="Stages all changes and commits them. Optionally pushes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The commit message (MUST follow Conventional Commits).",
                    },
                    "sync": {
                        "type": "boolean",
                        "description": "Whether to run 'git push' after committing.",
                        "default": False,
                    },
                },
                "required": ["message"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, object] | None
) -> list[types.TextContent]:
    """Handle tool execution requests from the IDE agent."""
    if name == "jitsu_get_next_phase":
        res = await _handle_get_next_phase()
    elif name == "jitsu_report_status":
        res = _handle_report_status(arguments)
    elif name == "jitsu_request_context":
        res = await _handle_request_context(arguments)
    elif name == "jitsu_inspect_queue":
        res = _handle_inspect_queue()
    elif name == "jitsu_get_planning_context":
        res = await _handle_get_planning_context(arguments)
    elif name == "jitsu_submit_epic":
        res = _handle_submit_epic(arguments)
    elif name == "jitsu_git_status":
        res = await _handle_git_status()
    elif name == "jitsu_git_commit":
        res = _handle_git_commit(arguments)
    else:
        msg = f"Unknown tool: {name}"
        raise ValueError(msg)

    return res


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
        epic_id = state_manager.update_phase_status(report)

        if report.status == PhaseStatus.SUCCESS and epic_id:
            count = state_manager.get_remaining_count(epic_id)
            msg = f"ACK. {count} phases remaining."
        else:
            msg = f"Successfully recorded status {report.status} for phase {report.phase_id}."

        return [types.TextContent(type="text", text=msg)]
    except ValidationError as e:
        return [types.TextContent(type="text", text=f"Validation Error: {e!s}")]


def _handle_inspect_queue() -> list[types.TextContent]:
    """Handle the 'inspect_queue' tool request."""
    pending = state_manager.get_pending_phases()
    if not pending:
        return [types.TextContent(type="text", text="The queue is currently empty.")]

    lines = ["Current Queue:"]
    lines.extend([f"- Phase: {item['phase_id']} (Epic: {item['epic_id']})" for item in pending])

    return [types.TextContent(type="text", text="\n".join(lines))]


async def _handle_request_context(arguments: dict[str, object] | None) -> list[types.TextContent]:
    """Handle the 'request_context' tool request."""
    if not arguments or "target_identifier" not in arguments:
        return [types.TextContent(type="text", text="Error: Missing target_identifier.")]

    target_id = str(arguments["target_identifier"])
    provider_name = str(arguments.get("provider_name", "file"))

    provider_cls = ProviderRegistry.get(provider_name)
    if not provider_cls:
        return [types.TextContent(type="text", text=f"Error: Unknown provider '{provider_name}'.")]

    provider = provider_cls(Path.cwd())
    context_data = await provider.resolve(target_id)
    return [types.TextContent(type="text", text=context_data)]


async def _handle_get_planning_context(
    _arguments: dict[str, object] | None,
) -> list[types.TextContent]:
    """Handle 'get_planning_context' tool request."""
    # 1. Get repo skeleton
    tree_provider = DirectoryTreeProvider(Path.cwd())
    skeleton = await tree_provider.resolve(".")

    # 2. Read .jitsurules
    rules_path = anyio.Path(Path.cwd()) / ".jitsurules"
    if await rules_path.exists():
        rules_content = await rules_path.read_text()
        rules_msg = f"### .jitsurules\n```text\n{rules_content}\n```"
    else:
        rules_msg = "### .jitsurules\n(Not found)"

    combined = f"{skeleton}\n\n{rules_msg}"
    return [types.TextContent(type="text", text=combined)]


def _handle_submit_epic(arguments: dict[str, object] | None) -> list[types.TextContent]:
    """Handle 'submit_epic' tool request."""
    if not arguments or "directives" not in arguments:
        return [types.TextContent(type="text", text="Error: Missing 'directives' argument.")]

    directives_data = arguments["directives"]
    if not isinstance(directives_data, list):
        return [types.TextContent(type="text", text="Error: 'directives' must be a list.")]

    try:
        directives = [
            AgentDirective.model_validate(d) for d in typing.cast("list[object]", directives_data)
        ]
        for directive in directives:
            state_manager.queue_directive(directive)

        return [
            types.TextContent(type="text", text=f"Successfully queued {len(directives)} phases.")
        ]
    except ValidationError as e:
        return [types.TextContent(type="text", text=f"Validation Error: {e!s}")]
    except Exception as e:  # noqa: BLE001
        return [types.TextContent(type="text", text=f"Internal Error: {e!s}")]


async def _handle_git_status() -> list[types.TextContent]:
    """Handle 'git_status' tool request."""
    provider = GitProvider(Path.cwd())
    res = await provider.resolve("status")
    return [types.TextContent(type="text", text=res)]


def _handle_git_commit(arguments: dict[str, object] | None) -> list[types.TextContent]:
    """Handle 'git_commit' tool request."""
    if not arguments or "message" not in arguments:
        return [types.TextContent(type="text", text="Error: Missing 'message' argument.")]

    message = str(arguments["message"])
    sync = bool(arguments.get("sync", False))

    # Conventional Commit Enforcement
    pattern = (
        r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert|deps)(\(.+\))?!?: .+$"
    )
    if not re.match(pattern, message):
        return [
            types.TextContent(
                type="text",
                text="Error: Commit message MUST follow Conventional Commits (e.g., 'feat: add git tool').",
            )
        ]

    try:
        # Delegate to JustFile recipes
        recipe = "sync" if sync else "commit"
        subprocess.run(
            ["/opt/homebrew/bin/just", recipe, message],
            check=True,
            shell=False,
            capture_output=True,
            text=True,
        )

        msg = f"Successfully committed{' and pushed' if sync else ''} changes."
        return [types.TextContent(type="text", text=msg)]
    except subprocess.CalledProcessError as e:
        error_msg = f"Error: Git command failed (exit code {e.returncode}): {e.stderr or e.stdout}"
        return [types.TextContent(type="text", text=error_msg)]


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
