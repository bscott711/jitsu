"""Tool handlers for the Jitsu MCP server."""

import contextlib
import json
import re
import subprocess
import sys
import tempfile
import typing
from pathlib import Path

import anyio
from anyio import to_thread
from mcp import types
from mcp.server import Server
from pydantic import ValidationError

from jitsu.core.compiler import ContextCompiler
from jitsu.core.planner import JitsuPlanner
from jitsu.core.runner import CommandRunner
from jitsu.core.state import JitsuStateManager
from jitsu.core.storage import EpicStorage
from jitsu.models.core import AgentDirective, PhaseReport, PhaseStatus
from jitsu.models.execution import PlannerOptions
from jitsu.providers import DirectoryTreeProvider, GitProvider, ProviderRegistry
from jitsu.server.registry import ToolRegistry


class ToolHandlers:
    """Handles tool execution logic for Jitsu."""

    def __init__(
        self,
        state_manager: JitsuStateManager,
        context_compiler: ContextCompiler,
        server: Server | None = None,
    ) -> None:
        """Initialize the tool handlers."""
        self.state_manager = state_manager
        self.context_compiler = context_compiler
        self.server = server

    async def handle_get_next_phase(self) -> list[types.TextContent]:
        """Handle the 'get_next_phase' tool request."""
        directive = self.state_manager.get_next_directive()
        if not directive:
            return [types.TextContent(type="text", text="No pending phases in the queue.")]

        compiled_markdown = await self.context_compiler.compile_directive(directive)
        return [types.TextContent(type="text", text=compiled_markdown)]

    def handle_report_status(self, arguments: dict[str, object] | None) -> list[types.TextContent]:
        """Handle the 'report_status' tool request."""
        if not arguments:
            return [types.TextContent(type="text", text="Error: Missing arguments.")]

        try:
            report = PhaseReport.model_validate(arguments)
            if report.status == PhaseStatus.STUCK:
                self.state_manager.on_stuck(report)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Epic HALTED. Phase {report.phase_id} is stuck and cannot progress.",
                    )
                ]

            epic_id = self.state_manager.update_phase_status(report)

            if report.status == PhaseStatus.SUCCESS and epic_id:
                count = self.state_manager.get_remaining_count(epic_id)
                msg = f"ACK. {count} phases remaining."
            else:
                msg = f"Successfully recorded status {report.status} for phase {report.phase_id}."

            return [types.TextContent(type="text", text=msg)]
        except ValidationError as e:
            return [types.TextContent(type="text", text=f"Validation Error: {e!s}")]

    def handle_inspect_queue(self) -> list[types.TextContent]:
        """Handle the 'inspect_queue' tool request."""
        pending = self.state_manager.get_pending_phases()
        if not pending:
            return [types.TextContent(type="text", text="The queue is currently empty.")]

        lines = ["Current Queue:"]
        lines.extend([f"- Phase: {item['phase_id']} (Epic: {item['epic_id']})" for item in pending])

        return [types.TextContent(type="text", text="\n".join(lines))]

    async def handle_request_context(
        self, arguments: dict[str, object] | None
    ) -> list[types.TextContent]:
        """Handle the 'request_context' tool request."""
        if not arguments or "target_identifier" not in arguments:
            return [types.TextContent(type="text", text="Error: Missing target_identifier.")]

        target_id = str(arguments["target_identifier"])
        provider_name = str(arguments.get("provider_name", "file"))

        provider_cls = ProviderRegistry.get(provider_name)
        if not provider_cls:
            return [
                types.TextContent(type="text", text=f"Error: Unknown provider '{provider_name}'.")
            ]

        provider = provider_cls(Path.cwd())
        context_data = await provider.resolve(target_id)
        return [types.TextContent(type="text", text=context_data)]

    async def handle_get_planning_context(
        self, _arguments: dict[str, object] | None
    ) -> list[types.TextContent]:
        """Handle 'get_planning_context' tool request."""
        tree_provider = DirectoryTreeProvider(Path.cwd())
        skeleton = await tree_provider.resolve(".")

        rules_path = anyio.Path(Path.cwd()) / ".jitsurules"
        if await rules_path.exists():
            rules_content = await rules_path.read_text()
            rules_msg = f"### .jitsurules\n```text\n{rules_content}\n```"
        else:
            rules_msg = "### .jitsurules\n(Not found)"

        combined = f"{skeleton}\n\n{rules_msg}"
        return [types.TextContent(type="text", text=combined)]

    def handle_submit_epic(self, arguments: dict[str, object] | None) -> list[types.TextContent]:
        """Handle 'submit_epic' tool request."""
        if not arguments or "directives" not in arguments:
            return [types.TextContent(type="text", text="Error: Missing 'directives' argument.")]

        directives_data = arguments["directives"]
        if not isinstance(directives_data, list):
            return [types.TextContent(type="text", text="Error: 'directives' must be a list.")]

        try:
            directives = [
                AgentDirective.model_validate(d)
                for d in typing.cast("list[object]", directives_data)
            ]
            for directive in directives:
                self.state_manager.queue_directive(directive)

            return [
                types.TextContent(
                    type="text", text=f"Successfully queued {len(directives)} phases."
                )
            ]
        except ValidationError as e:
            return [types.TextContent(type="text", text=f"Validation Error: {e!s}")]
        except RuntimeError as e:
            return [types.TextContent(type="text", text=f"Internal Error: {e!s}")]

    def _extract_progress_token(self, arguments: dict[str, object] | None) -> str | int | None:
        """Extract progress token from arguments metadata."""
        if not arguments:
            return None

        metadata = arguments.get("_metadata")
        if not isinstance(metadata, dict):
            return None

        metadata_dict = typing.cast("dict[typing.Any, typing.Any]", metadata)
        candidate = metadata_dict.get("progressToken")

        if isinstance(candidate, (str, int)):
            return candidate
        return None

    async def _send_progress_notification(self, token: str | int | None, message: str) -> None:
        """Send progress notification to MCP client if supported."""
        sys.stderr.write(f"[* progress] {message}\n")
        sys.stderr.flush()

        if token is not None and self.server:
            with contextlib.suppress(Exception):
                await self.server.request_context.session.send_progress_notification(
                    progress_token=token,
                    progress=0.0,
                )

    async def _create_progress_callback(
        self, arguments: dict[str, object] | None
    ) -> typing.Callable[[str], typing.Awaitable[None]]:
        """Create a progress callback closure with captured token."""
        token = self._extract_progress_token(arguments)

        async def on_progress(msg: str) -> None:
            await self._send_progress_notification(token, msg)

        return on_progress

    async def _execute_plan_workflow(
        self,
        prompt: str,
        relevant_files: list[str],
        on_progress: typing.Callable[[str], typing.Awaitable[None]],
    ) -> tuple[str, str] | None:
        """
        Execute the full planning workflow.

        Returns:
            Tuple of (epic_id, rel_path) on success, None on failure.

        """
        planner = JitsuPlanner(objective=prompt, relevant_files=relevant_files)
        await planner.generate_plan(options=PlannerOptions(on_progress=on_progress))

        if not planner.directives:
            return None

        if not planner.epic_id:
            return None

        storage = EpicStorage(Path.cwd())
        path = storage.get_current_path(planner.epic_id)
        planner.save_plan(path)
        rel_path = storage.rel_path(path)

        for directive in planner.directives:
            self.state_manager.queue_directive(directive)

        return (planner.epic_id, rel_path)

    async def handle_plan_epic(
        self, arguments: dict[str, object] | None
    ) -> list[types.TextContent]:
        """Handle 'plan_epic' tool request."""
        if not arguments or "prompt" not in arguments:
            return [types.TextContent(type="text", text="Error: Missing 'prompt' argument.")]

        prompt = str(arguments["prompt"])
        relevant_files = typing.cast("list[str]", arguments.get("relevant_files", []))

        on_progress = await self._create_progress_callback(arguments)
        result = await self._execute_plan_workflow(prompt, relevant_files, on_progress)

        if result is None:
            return [types.TextContent(type="text", text="Error: Failed to generate plan.")]

        epic_id, rel_path = result
        msg = (
            f"Successfully generated epic '{epic_id}' at '{rel_path}'.\n\n"
            "You can now call 'jitsu_get_next_phase' to begin execution of this epic."
        )
        return [types.TextContent(type="text", text=msg)]

    async def handle_git_status(self) -> list[types.TextContent]:
        """Handle 'git_status' tool request."""
        provider = GitProvider(Path.cwd())
        res = await provider.resolve("status")
        return [types.TextContent(type="text", text=res)]

    async def handle_check_coverage(
        self, arguments: dict[str, object] | None
    ) -> list[types.TextContent]:
        """Handle the 'jitsu_check_coverage' tool request."""
        try:
            error_msg: str | None = None
            result_text: str | None = None

            if (
                not arguments
                or "test_file_path" not in arguments
                or "module_scope" not in arguments
            ):
                error_msg = "Error in check_coverage: Missing 'test_file_path' or 'module_scope'."
            else:
                test_file = str(arguments["test_file_path"])
                module_scope = typing.cast("list[str]", arguments["module_scope"])

                if not await anyio.Path(test_file).exists():
                    error_msg = f"Error in check_coverage: Test file not found: {test_file}"
                elif not module_scope:
                    error_msg = "Error in check_coverage: 'module_scope' cannot be empty."
                else:
                    result_text = await self._run_scoped_coverage(test_file, module_scope)

            msg = error_msg or result_text or "Error: Unexpected empty result."
            return [types.TextContent(type="text", text=msg)]

        except Exception as e:  # noqa: BLE001
            return [types.TextContent(type="text", text=f"Error in check_coverage: {e!s}")]

    async def _run_scoped_coverage(self, test_file: str, module_scope: list[str]) -> str:
        """Run pytest with scoped coverage and return JSON string of results."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            temp_path = tmp.name

        try:
            cmd = [
                "pytest",
                "--cov=" + ",".join(module_scope),
                "--cov-report=json:" + temp_path,
                test_file,
            ]
            res = await to_thread.run_sync(lambda: CommandRunner.run_args(cmd, check=False))

            if res.returncode not in (0, 1):
                return f"Error in check_coverage: Pytest failed ({res.returncode}):\n{res.stderr or res.stdout}"

            path_obj = anyio.Path(temp_path)
            if not await path_obj.exists():
                return "Error in check_coverage: Coverage JSON file was not generated."

            content = await path_obj.read_text()
            data = json.loads(content)
            missing = {
                p: i["missing_lines"]
                for p, i in data.get("files", {}).items()
                if i.get("missing_lines")
            }

            return json.dumps(missing)
        finally:
            path_obj = anyio.Path(temp_path)
            if await path_obj.exists():
                await path_obj.unlink()

    def handle_git_commit(self, arguments: dict[str, object] | None) -> list[types.TextContent]:
        """Handle 'git_commit' tool request."""
        if not arguments or "message" not in arguments:
            return [types.TextContent(type="text", text="Error: Missing 'message' argument.")]

        message = str(arguments["message"])
        sync = bool(arguments.get("sync", False))

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
            recipe = "sync" if sync else "commit"
            res = CommandRunner.run_args(["just", recipe, message], check=True)
            del res

            msg = f"Successfully committed{' and pushed' if sync else ''} changes."
            return [types.TextContent(type="text", text=msg)]
        except subprocess.CalledProcessError as e:
            error_msg = (
                f"Error: Git command failed (exit code {e.returncode}): {e.stderr or e.stdout}"
            )
            return [types.TextContent(type="text", text=error_msg)]

    def register_all(self, registry: ToolRegistry) -> None:
        """Register all tools with the registry."""
        registry.register(
            types.Tool(
                name="jitsu_get_next_phase",
                description="Get the next Jitsu phase directive to execute.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            self.handle_get_next_phase,
        )

        registry.register(
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
            self.handle_report_status,
        )

        registry.register(
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
            self.handle_request_context,
        )

        registry.register(
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
            self.handle_get_planning_context,
        )

        registry.register(
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
            self.handle_submit_epic,
        )

        registry.register(
            types.Tool(
                name="jitsu_inspect_queue",
                description="Inspect the current queue of pending phases.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            self.handle_inspect_queue,
        )

        registry.register(
            types.Tool(
                name="jitsu_git_status",
                description="Returns the output of 'git status --short'.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            self.handle_git_status,
        )

        registry.register(
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
            self.handle_git_commit,
        )

        registry.register(
            types.Tool(
                name="jitsu_plan_epic",
                description="Plan a new epic from a high-level prompt.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The high-level objective for the new epic.",
                        },
                        "relevant_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of files relevant to the planning task.",
                        },
                    },
                    "required": ["prompt"],
                },
            ),
            self.handle_plan_epic,
        )

        registry.register(
            types.Tool(
                name="jitsu_check_coverage",
                description="Run scoped pytest coverage and return missing line numbers.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "test_file_path": {"type": "string"},
                        "module_scope": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["test_file_path", "module_scope"],
                },
            ),
            self.handle_check_coverage,
        )
