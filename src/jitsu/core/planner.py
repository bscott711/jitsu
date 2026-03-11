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
        model: str = "google/gemini-2.0-flash-001",
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
            base_system_prompt = "You are a helpful assistant."

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

        blueprint_system_prompt = base_system_prompt + (
            "\n\nCRITICAL MACRO RULE: You are drafting a high-level blueprint ONLY. "
            "You must return a SINGLE EpicBlueprint object. "
            "Each phase inside the blueprint MUST contain ONLY a `phase_id` and a 1-sentence `description`. "
            "Do NOT generate full instructions, module_scopes, context_targets, or any other fields yet. "
            "We will elaborate on those in a separate pass."
        )

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

            phase_system_prompt = base_system_prompt + (
                f"\n\nYou are elaborating a specific Phase for the Epic '{blueprint.epic_id}'.\n"
                f"Phase ID: {phase.phase_id}\n"
                f"Phase Description: {phase.description}\n"
                f"You MUST generate a single AgentDirective object that fulfills this phase's goals.\n\n"
                f"CRITICAL SCHEMA RULE: For any context_targets, you MUST ONLY use the following registered provider_names: [{allowed_providers}]. "
                "Do NOT use the provider you are currently building as a target."
                "CRITICAL GENERATION RULE: To prevent model degeneration, NEVER generate "
                "more than 5 items in ANY list or array (e.g., completion_criteria, anti_patterns).\n"
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
