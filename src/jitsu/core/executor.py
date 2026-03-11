"""Autonomous execution engine for Jitsu directives."""

import logging
import os
import shlex
import subprocess
from pathlib import Path

import dotenv
import instructor
import openai
import typer
from instructor.core.exceptions import InstructorRetryException
from openai import OpenAI

from jitsu.models.core import AgentDirective
from jitsu.models.execution import ExecutionResult

logger = logging.getLogger(__name__)


class JitsuExecutor:
    """Executes AgentDirectives autonomously using an LLM."""

    def __init__(self, model: str = "openai/gpt-oss-120b:free") -> None:
        """Initialize the executor with a model name."""
        self.model = model
        dotenv.load_dotenv()
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            msg = "OPENROUTER_API_KEY environment variable is not set"
            raise RuntimeError(msg)

        self.client = instructor.from_openai(
            OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            ),
            mode=instructor.Mode.JSON,
        )

    def execute_directive(self, directive: AgentDirective, compiler_output: str) -> bool:
        """Execute a single directive with retries on verification failure."""
        max_retries = 3
        attempts = 0
        last_error = ""

        while attempts <= max_retries:
            # 1. Call LLM to get ExecutionResult
            system_prompt = (
                "You are an autonomous coding agent. "
                "Given a directive and the relevant context, you must propose file edits "
                "to fulfill the task. Your output must be valid JSON matching the ExecutionResult schema.\n\n"
                f"Scope: {directive.module_scope}\n"
                f"Anti-Patterns: {', '.join(directive.anti_patterns)}\n"
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
                    res = subprocess.run(
                        shlex.split(cmd),
                        capture_output=True,
                        text=True,
                        check=False,
                    )
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
