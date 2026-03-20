"""Generates a sequence of AgentDirectives using an LLM."""

import inspect
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, get_args

import anyio
import typer
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

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
    TOOLCHAIN_CONSTRAINTS,
    VERIFICATION_RULE,
)
from jitsu.providers.tree import DirectoryTreeProvider

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class JitsuPlanner:
    """Generates a sequence of AgentDirectives using an LLM."""

    def __init__(
        self,
        objective: str,
        relevant_files: list[str],
        client: AsyncOpenAI | None = None,
        on_status: PlannerStatusCallback | None = None,
    ) -> None:
        self.objective = objective
        self.relevant_files = relevant_files
        self._client = client
        self.on_status = on_status
        self.directives: list[AgentDirective] = []
        self.epic_id: str | None = None

    async def _emit_status(
        self,
        stage: PlannerStage,
        message: str,
        progress_percent: float,
        on_progress: Callable[[str], Any] | None = None,
        on_status: PlannerStatusCallback | None = None,
    ) -> None:
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

        if on_progress:
            res = on_progress(message)
            if inspect.isawaitable(res):
                await res

    async def _generate_with_retry(
        self,
        client: AsyncOpenAI,
        model: str,
        messages: list[dict[str, str]],
        response_model: type[T],
        max_retries: int = 3,
    ) -> T:
        """Raw generation with regex JSON extraction and validation retry loop."""
        # Inject the schema requirement into the last message (usually user prompt)
        schema = json.dumps(response_model.model_json_schema())

        # FIX 1: messages is a list, so we must access an index (e.g., the last message)
        messages[-1]["content"] += (
            f"\n\nYou MUST output your response as a valid JSON object matching this schema:\n{schema}"
        )

        for attempt in range(max_retries):
            # FIX 2: Raw OpenAI client - no response_model parameter
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
            )

            # FIX 3: Access choices[0].message.content for raw OpenAI response
            content = response.choices[0].message.content or ""

            # Attempt to extract JSON block from markdown, or fallback to raw content
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
            json_str = match.group(1) if match else content

            try:
                # Strip leading/trailing whitespace that might break json parsing
                return response_model.model_validate_json(json_str.strip())
            except ValidationError as e:
                logger.warning(f"Validation failed on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to parse LLM output after {max_retries} attempts.\nRaw Output:\n{content}"
                    )
                    raise

                # Feed the error back to the LLM to fix
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Your previous response failed JSON validation:\n{e}\n\nPlease fix the errors and provide valid JSON.",
                    }
                )

    async def generate_plan(
        self,
        options: PlannerOptions | None = None,
    ) -> list[AgentDirective]:
        opts = options or PlannerOptions()
        _model = opts.model or settings.planner_model

        # FIX 4: Ensure we get a raw AsyncOpenAI client, not Instructor
        if self._client is not None:
            client = self._client
        else:
            client = LLMClientFactory.create()
            # If it's still an instructor client, unwrap it
            if hasattr(client, "client") and isinstance(client.client, AsyncOpenAI):
                client = client.client

        allowed_providers = ", ".join(
            get_args(ContextTarget.model_fields["provider_name"].annotation)
        )

        base_system_prompt = PLANNER_BASE_PROMPT
        rules_path = anyio.Path(".jitsurules")
        if await rules_path.exists():
            rules_text = await rules_path.read_text()
            base_system_prompt += f"\n\nPROJECT RULES (.jitsurules):\n{rules_text}"

        tree_provider = DirectoryTreeProvider(Path.cwd())
        skeleton = await tree_provider.resolve(".")

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
        blueprint = await self._generate_with_retry(
            client=client,
            model=_model,
            messages=[
                {"role": "system", "content": blueprint_system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_model=EpicBlueprint,
        )

        self.epic_id = blueprint.epic_id

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
        self.directives = []
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
                + f"\n{VERIFICATION_RULE}\n\n{TOOLCHAIN_CONSTRAINTS}\n"
            )

            directive = await self._generate_with_retry(
                client=client,
                model=_model,
                messages=[
                    {"role": "system", "content": phase_system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_model=AgentDirective,
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

        self.directives = self.compile_phases(
            self.directives,
            include_paths=opts.include_paths,
            exclude_paths=opts.exclude_paths,
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
        if not include_paths and not exclude_paths:
            return directives

        includes = include_paths or []
        excludes = set(exclude_paths or [])

        transformed_directives: list[AgentDirective] = []
        for directive in directives:
            new_targets: list[ContextTarget] = [
                target
                for target in directive.context_targets
                if target.target_identifier not in excludes
            ]

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

            transformed_directives.append(
                directive.model_copy(update={"context_targets": new_targets})
            )

        return transformed_directives

    def save_plan(self, path: str | Path) -> None:
        file_path = Path(path).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        json_data = [d.model_dump() for d in self.directives]
        file_path.write_text(json.dumps(json_data, indent=2))
