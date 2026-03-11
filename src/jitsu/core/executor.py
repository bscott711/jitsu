"""Autonomous execution engine for Jitsu directives."""

import logging
from pathlib import Path

import openai
import typer
from instructor.core.client import Instructor
from instructor.core.exceptions import InstructorRetryException

from jitsu.core.client import LLMClientFactory
from jitsu.core.runner import CommandRunner
from jitsu.models.core import AgentDirective
from jitsu.models.execution import ExecutionResult
from jitsu.prompts import EXECUTOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class JitsuExecutor:
    """Executes AgentDirectives autonomously using an LLM."""

    def __init__(
        self,
        model: str = "openai/gpt-oss-120b:free",
        client: Instructor | None = None,
        runner: CommandRunner | None = None,
    ) -> None:
        """
        Initialize the executor with a model name and optional LLM client.

        Args:
            model: The model name to use for LLM calls.
            client: An optional pre-constructed instructor client. If not provided,
                    one will be created via LLMClientFactory.
            runner: An optional CommandRunner instance. If not provided,
                    a default CommandRunner is used.

        """
        self.model = model
        self.client = client if client is not None else LLMClientFactory.create()
        self.runner = runner if runner is not None else CommandRunner()

    def execute_directive(self, directive: AgentDirective, compiler_output: str) -> bool:
        """Execute a single directive with retries on verification failure."""
        max_retries = 3
        attempts = 0
        last_error = ""

        while attempts <= max_retries:
            # 1. Call LLM to get ExecutionResult
            system_prompt = EXECUTOR_SYSTEM_PROMPT.format(
                module_scope=directive.module_scope,
                anti_patterns=", ".join(directive.anti_patterns),
            )

            user_message = (
                f"Directive: {directive.instructions}\n\n"
                f"Completion Criteria: {', '.join(directive.completion_criteria)}\n\n"
                f"Context:\n{compiler_output}\n"
            )

            if last_error:
                user_message += f"\n\nPREVIOUS VERIFICATION FAILURE:\n{last_error}\n"
                user_message += "Please fix the errors above."

            try:
                result = self.client.chat.completions.create(
                    model=self.model,
                    response_model=ExecutionResult,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                )

                # 2. Apply edits
                for edit in result.edits:
                    filepath = Path(edit.filepath).resolve()
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(edit.content)
                    logger.info("Updated file: %s", edit.filepath)

                # 3. Run verification
                verification_success = True
                all_stderr: list[str] = []
                for cmd in directive.verification_commands:
                    logger.info("Running verification: %s", cmd)
                    res = self.runner.run(cmd)
                    if res.returncode != 0:
                        verification_success = False
                        all_stderr.append(
                            f"Command '{cmd}' failed with exit code {res.returncode}:\n{res.stderr}"
                        )

                if verification_success:
                    logger.info("Verification passed!")
                    return True

                last_error = "\n".join(all_stderr)
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
            except Exception as e:
                logger.exception("Error during execution step")
                last_error = f"Execution error: {e!s}"
                attempts += 1

        return False
