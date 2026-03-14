"""Generates a sequence of AgentDirectives using an LLM."""

import inspect
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, get_args

import anyio
import typer
from instructor.core.client import Instructor

from jitsu.config import settings
from jitsu.core.client import LLMClientFactory
from jitsu.models.core import (
    AgentDirective,
    ContextTarget,
    EpicBlueprint,
    TargetResolutionMode,
)
from jitsu.models.execution import (
    PlannerOptions,
    PlannerStage,
    PlannerStatusCallback,
    PlannerStatusUpdate,
)
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

    def __init__(
        self,
        objective: str,
        relevant_files: list[str],
        client: Instructor | None = None,
        on_status: PlannerStatusCallback | None = None,
    ) -> None:
        """
        Initialize the planner with an objective, relevant files, and optional LLM client.

        Args:
            objective: The high-level goal for the plan.
            relevant_files: List of relevant file paths to include in context.
            client: An optional pre-constructed instructor client. If not provided,
                    one will be created via LLMClientFactory.
            on_status: An optional callback for structured status updates.

        """
        self.objective = objective
        self.relevant_files = relevant_files
        self._client = client
        self.on_status = on_status
        self.directives: list[AgentDirective] = []

    async def _emit_status(
        self,
        stage: PlannerStage,
        message: str,
        progress_percent: float,
        on_progress: Callable[[str], Any] | None = None,
        on_status: PlannerStatusCallback | None = None,
    ) -> None:
        """Centralized emitter for both legacy string and new structured status updates."""
        # 1. New structured callback
        callback = on_status or self.on_status
        if callback:
            update = PlannerStatusUpdate(
                stage=stage,
                message=message,
                progress_percent=progress_percent,
            )
            res = callback(update)
            if inspect.isawaitable(res):
                await res

        # 2. Legacy string callback
        if on_progress:
            res = on_progress(message)
            if inspect.isawaitable(res):
                await res

    async def generate_plan(
        self,
        options: PlannerOptions | None = None,
    ) -> list[AgentDirective]:
        """Query the LLM and generate a validated list of directives using two passes."""
        opts = options or PlannerOptions()
        _model = opts.model or settings.planner_model
        client = self._client if self._client is not None else LLMClientFactory.create()

        # Extract allowed provider names for prompt engineering
        allowed_providers = ", ".join(
            get_args(ContextTarget.model_fields["provider_name"].annotation)
        )

        base_system_prompt = PLANNER_BASE_PROMPT

        # Dynamically inject the project-specific rules
        rules_path = anyio.Path(".jitsurules")
        if await rules_path.exists():
            rules_text = await rules_path.read_text()
            base_system_prompt += f"\n\nPROJECT RULES (.jitsurules):\n{rules_text}"

        # Get repository skeleton
        tree_provider = DirectoryTreeProvider(Path.cwd())
        skeleton = await tree_provider.resolve(".")

        # Build the user message
        files_str = "\n".join(f"- {f}" for f in self.relevant_files)
        user_message = (
            f"Repository Skeleton:\n{skeleton}\n\n"
            f"Objective: {self.objective}\n\n"
            f"Relevant Files:\n{files_str}"
        )

        await self._emit_status(
            PlannerStage.ANALYZING_SCOPE,
            "Analyzing project scope...",
            10.0,
            opts.on_progress,
            opts.on_status,
        )

        # Pass 1: Macro - Generate Epic Blueprint
        await self._emit_status(
            PlannerStage.DRAFTING_PHASES,
            "Drafting Epic Blueprint...",
            20.0,
            opts.on_progress,
            opts.on_status,
        )

        blueprint_system_prompt = base_system_prompt + PLANNER_MACRO_PROMPT

        blueprint = client.chat.completions.create(
            model=_model,
            response_model=EpicBlueprint,
            messages=[
                {"role": "system", "content": blueprint_system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        if opts.verbose:
            typer.secho("\n[DEBUG] Epic Blueprint:", fg=typer.colors.YELLOW, bold=True, err=True)
            typer.secho(blueprint.model_dump_json(indent=2), fg=typer.colors.YELLOW, err=True)

        await self._emit_status(
            PlannerStage.ANALYZING_SCOPE,
            "Analyzing module scope and drafting phases...",
            40.0,
            opts.on_progress,
            opts.on_status,
        )

        # Pass 2: Micro - Elaborate each phase
        self.directives: list[AgentDirective] = []
        for i, phase in enumerate(blueprint.phases):
            progress = 40.0 + (50.0 * (i / len(blueprint.phases)))
            await self._emit_status(
                PlannerStage.DRAFTING_PHASES,
                f"Elaborating Phase {i + 1} of {len(blueprint.phases)} ({phase.phase_id})...",
                progress,
                opts.on_progress,
                opts.on_status,
            )

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
                model=_model,
                response_model=AgentDirective,
                messages=[
                    {"role": "system", "content": phase_system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )

            if opts.verbose:
                typer.secho(
                    f"\n[DEBUG] Phase {i + 1} Directive ({phase.phase_id}):",
                    fg=typer.colors.CYAN,
                    bold=True,
                    err=True,
                )
                typer.secho(directive.model_dump_json(indent=2), fg=typer.colors.CYAN, err=True)

            self.directives.append(directive)

        await self._emit_status(
            PlannerStage.VALIDATING_SCHEMA,
            "Validating schema and finalizing project scope...",
            90.0,
            opts.on_progress,
            opts.on_status,
        )

        # Apply deterministic context injection/exclusion
        self.directives = self.compile_phases(
            self.directives, include_paths=opts.include_paths, exclude_paths=opts.exclude_paths
        )

        await self._emit_status(
            PlannerStage.COMPLETE, "Planning complete.", 100.0, opts.on_progress, opts.on_status
        )

        return self.directives

    def compile_phases(
        self,
        directives: list[AgentDirective],
        include_paths: list[str] | None = None,
        exclude_paths: list[str] | None = None,
    ) -> list[AgentDirective]:
        """
        Deterministically transform the list of directives by injecting and excluding context.

        Args:
            directives: The list of AgentDirectives to transform.
            include_paths: Optional list of file paths to inject into every phase.
            exclude_paths: Optional list of file paths to strip from every phase.

        Returns:
            A new list of transformed AgentDirectives.

        """
        if not include_paths and not exclude_paths:
            return directives

        includes = include_paths or []
        excludes = set(exclude_paths or [])

        transformed_directives: list[AgentDirective] = []
        for directive in directives:
            # 1. Start with existing targets, but filter out excluded ones
            new_targets: list[ContextTarget] = [
                target
                for target in directive.context_targets
                if target.target_identifier not in excludes
            ]

            # 2. Add included files if not already present
            existing_identifiers = {t.target_identifier for t in new_targets}
            new_targets.extend(
                [
                    ContextTarget(
                        provider_name="file",
                        target_identifier=path,
                        is_required=True,
                        resolution_mode=TargetResolutionMode.FULL_SOURCE,
                    )
                    for path in includes
                    if path not in existing_identifiers
                ]
            )

            # 3. Create a copy of the directive with updated targets
            transformed_directives.append(
                directive.model_copy(update={"context_targets": new_targets})
            )

        return transformed_directives

    def save_plan(self, path: str | Path) -> None:
        """Save the generated plan to disk as a JSON file."""
        file_path = Path(path).resolve()

        # Ensure parent directories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Pydantic v2 model_dump for the list
        json_data = [d.model_dump() for d in self.directives]
        file_path.write_text(json.dumps(json_data, indent=2))
