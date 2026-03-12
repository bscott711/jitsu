"""Autonomous execution engine for Jitsu directives."""

import logging
import re
from pathlib import Path

import openai
import typer
from instructor.core.client import Instructor
from instructor.core.exceptions import InstructorRetryException

from jitsu.core.client import LLMClientFactory
from jitsu.core.runner import CommandRunner
from jitsu.models.core import AgentDirective
from jitsu.models.execution import ExecutionResult, FileEdit
from jitsu.prompts import (
    EXECUTOR_RECOVERY_PROMPT,
    EXECUTOR_SYSTEM_PROMPT,
    VERIFICATION_SUMMARY_RULE,
)
from jitsu.providers.ast import ASTProvider

logger = logging.getLogger(__name__)


class MonotonicityError(Exception):
    """Raised when the agent fails to improve or makes the situation worse."""


class JitsuExecutor:
    """Executes AgentDirectives autonomously using an LLM."""

    def __init__(
        self,
        model: str = "openai/gpt-oss-120b:free",
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
        self.model = model
        self.client = client if client is not None else LLMClientFactory.create()
        self.runner = runner if runner is not None else CommandRunner()
        self.workspace_root = workspace_root or Path.cwd()
        self.ast_provider = ASTProvider(self.workspace_root)

    @staticmethod
    def _apply_edits(edits: list[FileEdit]) -> None:
        """Safely write file edits to disk."""
        for edit in edits:
            filepath = Path(edit.filepath).resolve()
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(edit.content)
            logger.info("Updated file: %s", edit.filepath)

    @staticmethod
    def _extract_first_failure_block(stderr: str) -> tuple[str, str | None]:
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
    def _parse_failure_count(stderr: str) -> int:
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

    def _run_verification(self, commands: list[str]) -> tuple[bool, str, str, str, str | None]:
        """Execute verification commands and aggregate errors."""
        for cmd in commands:
            logger.info("Running verification: %s", cmd)
            res = self.runner.run(cmd)
            if res.returncode != 0:
                fail_count = self._parse_failure_count(res.stderr)
                summary = (
                    f"Command '{cmd}' failed with {fail_count} errors (exit code {res.returncode})"
                )
                trimmed_block, failing_file = self._extract_first_failure_block(res.stderr)
                return False, summary, trimmed_block, cmd, failing_file

        logger.info("Verification passed!")
        return True, "", "", "", None

    async def execute_directive(self, directive: AgentDirective, compiler_output: str) -> bool:
        """Execute a single directive with retries on verification failure."""
        max_retries = 3
        attempts = 0
        prev_fail_count = float("inf")

        system_prompt = EXECUTOR_SYSTEM_PROMPT.format(
            module_scope=directive.module_scope,
            anti_patterns=", ".join(directive.anti_patterns),
        )

        base_user_message = (
            f"Directive: {directive.instructions}\n\n"
            f"Completion Criteria: {', '.join(directive.completion_criteria)}\n\n"
            f"Context:\n{compiler_output}\n"
        )

        while attempts <= max_retries:
            user_message = base_user_message

            try:
                result = self.client.chat.completions.create(
                    model=self.model,
                    response_model=ExecutionResult,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                )

                if attempts > 0:
                    self._enforce_scope(result.edits, directive.module_scope)

                self._apply_edits(result.edits)

                success, summary, trimmed, _failed_cmd, failing_file = self._run_verification(
                    directive.verification_commands
                )
                if success:
                    return True

                prev_fail_count = self._check_monotonicity(summary, prev_fail_count)
                base_user_message = await self._augment_recovery_message(
                    base_user_message, summary, trimmed, result.edits, failing_file
                )

                attempts += 1
                logger.warning(
                    "Verification failed (Attempt %d/%d). Retrying...",
                    attempts,
                    max_retries + 1,
                )

            except openai.APIStatusError as e:
                typer.secho(
                    f"\n❌ Execution API Error [{e.status_code}]: {e.message}",
                    fg=typer.colors.RED,
                    err=True,
                )
                return False
            except InstructorRetryException:
                typer.secho(
                    "\n❌ Executor Error: Failed to generate valid schema.",
                    fg=typer.colors.RED,
                    err=True,
                )
                return False
            except MonotonicityError:
                raise
            except Exception as e:
                logger.exception("Error during execution step")
                base_user_message += f"\n\nExecution error: {e!s}\n"
                attempts += 1

        return False

    def _enforce_scope(self, edits: list[FileEdit], module_scope: str) -> None:
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

            if not path.as_posix().startswith(module_scope):
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

    async def _augment_recovery_message(
        self,
        base_message: str,
        summary: str,
        trimmed: str,
        edits: list[FileEdit],
        failing_file: str | None = None,
    ) -> str:
        """Append recovery hint, failure details, and AST context to the user message."""
        payload = (
            EXECUTOR_RECOVERY_PROMPT
            + "\n\n"
            + VERIFICATION_SUMMARY_RULE.format(summary=summary, trimmed_block=trimmed)
        )

        # Collect all relevant files for AST resolution
        files_to_resolve = {edit.filepath for edit in edits if edit.filepath.endswith(".py")}

        if failing_file and failing_file.endswith(".py"):
            # Ensure failing file is within workspace root before allowing resolution
            failing_path = Path(failing_file)
            is_internal = True
            if failing_path.is_absolute():
                try:
                    failing_path.relative_to(self.workspace_root)
                except ValueError:
                    is_internal = False
                    logger.warning("Failing file %s is outside workspace root", failing_file)

            if is_internal:
                files_to_resolve.add(failing_file)

        for filepath in sorted(files_to_resolve):
            ast_ctx = await self.ast_provider.resolve(filepath)
            payload += f"\n\n{ast_ctx}"

        return base_message + f"\n\n{payload}\nPlease fix the errors above."
