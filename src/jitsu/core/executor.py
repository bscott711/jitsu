"""Autonomous execution engine for Jitsu directives."""

import logging
import re
from pathlib import Path

import openai
import typer
from instructor.core.client import Instructor
from instructor.core.exceptions import InstructorRetryException
from openai.types.chat import ChatCompletionMessageParam

from jitsu.config import settings
from jitsu.core.client import LLMClientFactory
from jitsu.core.runner import CommandRunner
from jitsu.models.core import AgentDirective
from jitsu.models.execution import (
    ExecutionResult,
    FileEdit,
    ToolRequest,
    VerificationFailureDetails,
)
from jitsu.prompts import (
    EXECUTOR_RECOVERY_PROMPT,
    EXECUTOR_SYSTEM_PROMPT,
    VERIFICATION_SUMMARY_RULE,
)
from jitsu.providers.ast import ASTProvider
from jitsu.providers.file import FileStateProvider
from jitsu.providers.registry import ProviderRegistry
from jitsu.utils.traceback_parser import extract_filepaths, filter_local_paths

logger = logging.getLogger(__name__)


class MonotonicityError(Exception):
    """Raised when the agent fails to improve or makes the situation worse."""


class JitsuExecutor:
    """Executes AgentDirectives autonomously using an LLM."""

    def __init__(
        self,
        model: str | None = None,
        client: Instructor | None = None,
        runner: CommandRunner | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        """
        Initialize the executor with a model name and optional LLM client.

        Args:
            model: The model name to use for LLM calls.
            client: An optional pre-constructed instructor client. If not provided,
                    one will be created via LLMClientFactory.
            runner: An optional CommandRunner instance. If not provided,
                    a default CommandRunner is used.
            workspace_root: The root directory of the workspace.

        """
        self.model = model or settings.executor_model
        self.client = client if client is not None else LLMClientFactory.create()
        self.runner = runner if runner is not None else CommandRunner()
        self.workspace_root = workspace_root or Path.cwd()
        self.ast_provider = ASTProvider(self.workspace_root)
        self.file_provider = FileStateProvider(self.workspace_root)

    async def _execute_tool(self, tool_request: ToolRequest) -> str:
        """Execute a tool via Jitsu Providers and return its output."""
        provider_cls = ProviderRegistry.get(tool_request.tool_name)
        if not provider_cls:
            return f"Error: Unknown tool '{tool_request.tool_name}'"

        provider = provider_cls(self.workspace_root)

        # Extraction logic: use 'target', 'path' or first argument as the resolution target
        target = (
            tool_request.arguments.get("target")
            or tool_request.arguments.get("path")
            or tool_request.arguments.get("target_identifier")
            or (next(iter(tool_request.arguments.values()), "") if tool_request.arguments else "")
        )

        return await provider.resolve(str(target))

    async def _run_react_loop(
        self, messages: list[ChatCompletionMessageParam]
    ) -> list[FileEdit] | None:
        """Run the ReAct tool calling loop and return the resulting file edits."""
        tool_turns = 0
        max_tool_turns = 5
        while tool_turns < max_tool_turns:
            result = self.client.chat.completions.create(
                model=self.model,
                response_model=ExecutionResult,
                messages=messages,
            )

            if isinstance(result.action, ToolRequest):
                tool_turns += 1
                logger.info("Executing tool: %s", result.action.tool_name)
                tool_output = await self._execute_tool(result.action)

                # Maintain ReAct history
                messages.append({"role": "assistant", "content": result.model_dump_json()})
                messages.append({"role": "user", "content": f"Tool output:\n{tool_output}"})
                continue

            return result.action

        logger.warning("Max tool turns reached (circuit breaker triggered)")
        return None

    @staticmethod
    def _apply_edits(edits: list[FileEdit]) -> None:
        """Safely write file edits to disk."""
        for edit in edits:
            filepath = Path(edit.filepath).resolve()
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(edit.content)
            logger.info("Updated file: %s", edit.filepath)

    @staticmethod
    def extract_first_failure_block(stderr: str) -> tuple[str, str | None]:
        """Isolate the first actionable error block and parse the failing file path."""
        # 1. Pytest style
        # Look for ____ test_name ____ ... block
        pytest_match = re.search(r"_{4,}\s+(.*?)\s+_{4,}(.*?)(?=\n_{4,}|$)", stderr, re.DOTALL)
        if pytest_match:
            block = pytest_match.group(0).strip()
            # Extract file path from pytest block (usually at the end of the block)
            # e.g., "tests/core/test_executor.py:302: AssertionError"
            file_match = re.search(r"^([\w\.\-/]+\.py):(\d+):", block, re.MULTILINE)
            if file_match:
                return block, file_match.group(1)
            return block, None

        # 2. Ruff/Pyright/Generic file:line style
        # e.g., src/jitsu/core/executor.py:92:9: error: ...
        generic_match = re.search(r"^([\w\.\-/]+\.py):(\d+):(?:\d+:)?\s+(.*)", stderr, re.MULTILINE)
        if generic_match:
            # For generic errors, just take the first few lines around the error
            lines = stderr.splitlines()
            for i, line in enumerate(lines):
                if generic_match.group(0) in line:
                    return "\n".join(lines[i : i + 10]), generic_match.group(1)

        # Fallback to 20 lines if all else fails
        lines = stderr.splitlines()
        return "\n".join(lines[:20]), None

    @staticmethod
    def parse_failure_count(stderr: str) -> int:
        """Attempt to extract an error/failure count from command output."""
        # pytest: "1 failed", ruff: "Found 4 errors", etc.
        patterns = [
            r"(\d+) failed",
            r"Found (\d+) error",
            r"(\d+) error(?:s)? found",
            r"(\d+) errors",
        ]
        for pattern in patterns:
            match = re.search(pattern, stderr, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 1  # Default to 1 if we can't find a count

    def run_verification(
        self, commands: list[str]
    ) -> tuple[bool, VerificationFailureDetails | None]:
        """Execute verification commands and aggregate errors."""
        for cmd in commands:
            logger.info("Running verification: %s", cmd)
            res = self.runner.run(cmd)
            if res.returncode != 0:
                fail_count = self.parse_failure_count(res.stderr)
                summary = (
                    f"Command '{cmd}' failed with {fail_count} errors (exit code {res.returncode})"
                )
                trimmed_block, failing_file = self.extract_first_failure_block(res.stderr)
                details = VerificationFailureDetails(
                    summary=summary,
                    trimmed=trimmed_block,
                    failed_cmd=cmd,
                    failing_file=failing_file,
                )
                return False, details

        logger.info("Verification passed!")
        return True, None

    async def execute_directive(
        self,
        directive: AgentDirective,
        compiler_output: str,
        max_retries: int = 5,
    ) -> bool:
        """Execute a single directive with retries on verification failure."""
        attempts = 0
        prev_fail_count = float("inf")
        base_user_message = (
            f"Directive: {directive.instructions}\n"
            f"Scope: {directive.module_scope}\n"
            f"Anti-Patterns: {', '.join(directive.anti_patterns)}\n\n"
            f"Completion Criteria: {', '.join(directive.completion_criteria)}\n\n"
            f"Context:\n{compiler_output}\n"
        )

        while attempts <= max_retries:
            success, base_user_message, prev_fail_count = await self._execute_attempt_cycle(
                directive, base_user_message, attempts, prev_fail_count
            )
            if success:
                return True
            if base_user_message is None:
                return False
            attempts += 1

        return False

    async def _execute_attempt_cycle(
        self,
        directive: AgentDirective,
        base_user_message: str,
        attempts: int,
        prev_fail_count: float,
    ) -> tuple[bool, str | None, float]:
        """Perform one cycle of LLM generation, edit application, and verification."""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
            {"role": "user", "content": base_user_message},
        ]

        try:
            edits = await self._run_react_loop(messages)
            if edits is None:
                return False, None, prev_fail_count

            if attempts > 0:
                self.enforce_scope(edits, directive.module_scope)

            self._apply_edits(edits)
            success, details = self.run_verification(directive.verification_commands)
        except (openai.APIStatusError, InstructorRetryException) as e:
            self._report_api_issue(e)
            return False, None, prev_fail_count
        except MonotonicityError:
            raise
        except Exception as e:
            logger.exception("Error during execution step")
            return False, base_user_message + f"\n\nExecution error: {e!s}\n", prev_fail_count
        else:
            if success:
                return True, base_user_message, prev_fail_count

            if details is None:
                return False, None, prev_fail_count

            new_fail_count, augmented_message = await self._handle_attempt_failure(
                base_user_message, details, edits, directive, prev_fail_count
            )
            logger.warning("Verification failed (Attempt %d). Retrying...", attempts + 1)
            return False, augmented_message, new_fail_count

    def _report_api_issue(self, e: Exception) -> None:
        """Report API or schema generation errors to the user."""
        if isinstance(e, openai.APIStatusError):
            typer.secho(
                f"\n❌ Execution API Error [{e.status_code}]: {e.message}", fg="red", err=True
            )
        else:
            typer.secho("\n❌ Executor Error: Failed to generate valid schema.", fg="red", err=True)

    async def _handle_attempt_failure(
        self,
        base_user_message: str,
        details: VerificationFailureDetails,
        edits: list[FileEdit],
        directive: AgentDirective,
        prev_fail_count: float,
    ) -> tuple[float, str]:
        """Handle a verification failure by checking monotonicity and augmenting the prompt."""
        new_fail_count = self._check_monotonicity(details.summary, prev_fail_count)
        augmented_message = await self.augment_recovery_message(
            base_user_message, details, edits, directive
        )
        return float(new_fail_count), augmented_message

    def enforce_scope(self, edits: list[FileEdit], module_scope: list[str]) -> None:
        """Ensure all edits are within the allowed module scope."""
        for edit in edits:
            path = Path(edit.filepath)
            # If absolute, try making it relative to workspace_root
            if path.is_absolute():
                try:
                    path = path.relative_to(self.workspace_root)
                except ValueError:
                    # Not under workspace_root, definitely out of scope
                    msg = f"FileEdit path '{edit.filepath}' is outside workspace_root."
                    raise MonotonicityError(msg) from None

            posix_path = path.as_posix()
            if not any(posix_path.startswith(scope) for scope in module_scope):
                msg = (
                    f"FileEdit path '{edit.filepath}' is outside module_scope "
                    f"'{module_scope}' during retry."
                )
                raise MonotonicityError(msg)

    def _check_monotonicity(self, summary: str, prev_fail_count: float) -> int:
        """Verify that the error count has improved, otherwise raise MonotonicityError."""
        fail_match = re.search(r"(\d+) errors", summary)
        fail_count = int(fail_match.group(1)) if fail_match else 1

        if fail_count >= prev_fail_count:
            msg = (
                f"Retry failed to improve error count (Current: {fail_count}, "
                f"Prev: {prev_fail_count}). Aborting."
            )
            raise MonotonicityError(msg)
        return fail_count

    async def augment_recovery_message(
        self,
        base_message: str,
        details: VerificationFailureDetails,
        edits: list[FileEdit],
        directive: AgentDirective,
    ) -> str:
        """Append recovery hint, failure details, and AST context to the user message."""
        payload = (
            EXECUTOR_RECOVERY_PROMPT
            + "\n\n"
            + VERIFICATION_SUMMARY_RULE.format(
                summary=details.summary,
                failed_cmd=details.failed_cmd,
                trimmed_block=details.trimmed,
            )
        )

        # Collect all relevant files for AST resolution
        files_to_resolve = {edit.filepath for edit in edits if edit.filepath.endswith(".py")}

        if details.failing_file and details.failing_file.endswith(".py"):
            # Ensure failing file is within workspace root before allowing resolution
            failing_path = Path(details.failing_file)
            is_internal = True
            if failing_path.is_absolute():
                try:
                    failing_path.relative_to(self.workspace_root)
                except ValueError:
                    is_internal = False
                    logger.warning(
                        "Failing file %s is outside workspace root", details.failing_file
                    )

            if is_internal:
                files_to_resolve.add(details.failing_file)

        # Dynamic Context Expansion: Parse traceback for more relevant files
        extracted_paths = extract_filepaths(details.trimmed)
        local_paths = filter_local_paths(extracted_paths, self.workspace_root)

        for filepath in sorted(local_paths):
            # 1. Must be in module_scope
            in_scope = any(filepath.startswith(scope) for scope in directive.module_scope)
            if not in_scope:
                continue

            # 2. Must NOT be in the base_message already
            # We check both full source and manifest indicators
            if f"`{filepath}`" in base_message or f"### File: {filepath}" in base_message:
                continue

            # 3. Load full source and append
            logger.info("Found out-of-context file in traceback: %s. Expanding context.", filepath)
            file_ctx = await self.file_provider.resolve(filepath)
            payload += f"\n\n{file_ctx}"

        for filepath in sorted(files_to_resolve):
            ast_ctx = await self.ast_provider.resolve(filepath)
            payload += f"\n\n{ast_ctx}"

        return base_message + f"\n\n{payload}\nPlease fix the errors above."
