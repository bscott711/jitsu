"""Generates a sequence of AgentDirectives using an LLM."""

import json
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import get_args

import anyio
import dotenv
import instructor
import typer
from openai import OpenAI

from jitsu.models.core import AgentDirective, ContextTarget, EpicBlueprint
from jitsu.prompts import (
    PLANNER_BASE_PROMPT,
    PLANNER_MACRO_PROMPT,
    PLANNER_MICRO_PROMPT,
    VERIFICATION_RULE,
)
from jitsu.providers.tree import DirectoryTreeProvider

logger = logging.getLogger(__name__)


class JitsuPlanner:
    """Generates a sequence of AgentDirectives using an LLM."""

    def __init__(self, objective: str, relevant_files: list[str]) -> None:
        """Initialize the planner with an objective and relevant files."""
        self.objective = objective
        self.relevant_files = relevant_files
        self._directives: list[AgentDirective] = []

    async def generate_plan(
        self,
        model: str = "openai/gpt-oss-120b:free",
        on_progress: Callable[[str], None] | None = None,
        *,
        verbose: bool = False,
    ) -> list[AgentDirective]:
        """Query the LLM and generate a validated list of directives using two passes."""
        dotenv.load_dotenv()

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            msg = "OPENROUTER_API_KEY environment variable is not set"
            raise RuntimeError(msg)

        # Initialize instructor with OpenAI client pointing to OpenRouter
        client = instructor.from_openai(
            OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            ),
            mode=instructor.Mode.JSON,
        )

        # Extract allowed provider names for prompt engineering
        allowed_providers = ", ".join(
            get_args(ContextTarget.model_fields["provider_name"].annotation)
        )

        # Read the core orchestrator prompt
        prompt_path = anyio.Path("docs/jitsu_orchestrator_prompt.md")
        if await prompt_path.exists():
            base_system_prompt = await prompt_path.read_text()
        else:
            base_system_prompt = PLANNER_BASE_PROMPT

        # Dynamically inject the project-specific rules
        rules_path = anyio.Path(".jitsurules")
        if await rules_path.exists():
            rules_text = await rules_path.read_text()
            base_system_prompt += f"\n\nPROJECT RULES (.jitsurules):\n{rules_text}"

        # Get repository skeleton
        tree_provider = DirectoryTreeProvider()
        skeleton = await tree_provider.resolve(str(Path.cwd()))

        # Build the user message
        files_str = "\n".join(f"- {f}" for f in self.relevant_files)
        user_message = (
            f"Repository Skeleton:\n{skeleton}\n\n"
            f"Objective: {self.objective}\n\n"
            f"Relevant Files:\n{files_str}"
        )

        # Pass 1: Macro - Generate Epic Blueprint
        if on_progress:
            on_progress("Drafting Epic Blueprint...")

        blueprint_system_prompt = base_system_prompt + PLANNER_MACRO_PROMPT

        blueprint = client.chat.completions.create(
            model=model,
            response_model=EpicBlueprint,
            messages=[
                {"role": "system", "content": blueprint_system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        if verbose:
            typer.secho("\n[DEBUG] Epic Blueprint:", fg=typer.colors.YELLOW, bold=True, err=True)
            typer.secho(blueprint.model_dump_json(indent=2), fg=typer.colors.YELLOW, err=True)

        # Pass 2: Micro - Elaborate each phase
        self._directives = []
        for i, phase in enumerate(blueprint.phases):
            if on_progress:
                on_progress(f"Elaborating Phase {i + 1} of {len(blueprint.phases)}...")

            phase_system_prompt = (
                base_system_prompt
                + PLANNER_MICRO_PROMPT.format(
                    epic_id=blueprint.epic_id,
                    phase_id=phase.phase_id,
                    phase_description=phase.description,
                    allowed_providers=allowed_providers,
                )
                + f"\n{VERIFICATION_RULE}\n"
            )

            directive = client.chat.completions.create(
                model=model,
                response_model=AgentDirective,
                messages=[
                    {"role": "system", "content": phase_system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )

            if verbose:
                typer.secho(
                    f"\n[DEBUG] Phase {i + 1} Directive ({phase.phase_id}):",
                    fg=typer.colors.CYAN,
                    bold=True,
                    err=True,
                )
                typer.secho(directive.model_dump_json(indent=2), fg=typer.colors.CYAN, err=True)

            self._directives.append(directive)

        return self._directives

    def save_plan(self, path: str | Path) -> None:
        """Save the generated plan to disk as a JSON file."""
        file_path = Path(path).resolve()

        # Ensure parent directories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Pydantic v2 model_dump for the list
        json_data = [d.model_dump() for d in self._directives]
        file_path.write_text(json.dumps(json_data, indent=2))
