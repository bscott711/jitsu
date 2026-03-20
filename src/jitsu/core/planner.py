"""Generates a sequence of AgentDirectives using an LLM."""

import inspect
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, get_args

import anyio
from instructor.core.client import Instructor
from pydantic import BaseModel

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
        client: Instructor | None = None,
        on_status: PlannerStatusCallback | None = None,
    ) -> None:
        """Initialize the planner with an objective and context."""
        self.objective = objective
        self.relevant_files = relevant_files
        self._client = client
        self.on_status = on_status
        self.directives: list[AgentDirective] = []
        self.epic_id: str | None = None

    def _parse_llm_json(self, raw_content: str, model_class: type[T]) -> T:
        """Extract and validate JSON from raw LLM output to bypass instructor retries."""
        match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        json_str = match.group(0) if match else raw_content

        try:
            parsed_data = json.loads(json_str)
            return model_class.model_validate(parsed_data)
        except (json.JSONDecodeError, ValueError) as e:
            msg = f"Failed to parse {model_class.__name__} from raw output:\n{raw_content}"
            raise RuntimeError(msg) from e

    async def _emit_status(
        self,
        stage: PlannerStage,
        message: str,
        progress_percent: float,
        on_progress: Callable[[str], Any] | None = None,
        on_status: PlannerStatusCallback | None = None,
    ) -> None:
        """Centralized emitter for status updates."""
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

    async def generate_plan(
        self,
        options: PlannerOptions | None = None,
    ) -> list[AgentDirective]:
        """Query the LLM and generate a validated list of directives using two passes."""
        opts = options or PlannerOptions()
        _model = opts.model or settings.planner_model
        client = self._client if self._client is not None else LLMClientFactory.create()

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
            "Analyzing scope...",
            10.0,
            opts.on_progress,
            opts.on_status,
        )

        # Pass 1: Macro - Generate Epic Blueprint
        await self._emit_status(
            PlannerStage.DRAFTING_PHASES,
            "Drafting Blueprint...",
            20.0,
            opts.on_progress,
            opts.on_status,
        )

        if client.client is None:
            msg = "Underlying LLM client is not initialized"
            raise RuntimeError(msg)
        blueprint_resp = client.client.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": base_system_prompt + PLANNER_MACRO_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        blueprint = self._parse_llm_json(
            blueprint_resp.choices[0].message.content or "{}", EpicBlueprint
        )
        self.epic_id = blueprint.epic_id

        # Pass 2: Micro - Elaborate each phase
        self.directives = []
        for i, phase in enumerate(blueprint.phases):
            progress = 40.0 + (50.0 * (i / len(blueprint.phases)))
            await self._emit_status(
                PlannerStage.DRAFTING_PHASES,
                f"Elaborating Phase {i + 1} ({phase.phase_id})...",
                progress,
                opts.on_progress,
                opts.on_status,
            )

            phase_prompt = (
                base_system_prompt
                + PLANNER_MICRO_PROMPT.format(
                    epic_id=blueprint.epic_id,
                    phase_id=phase.phase_id,
                    phase_description=phase.description,
                    allowed_providers=allowed_providers,
                )
                + f"\n{VERIFICATION_RULE}\n\n{TOOLCHAIN_CONSTRAINTS}\n"
            )

            phase_resp = client.client.chat.completions.create(
                model=_model,
                messages=[
                    {"role": "system", "content": phase_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            directive = self._parse_llm_json(
                phase_resp.choices[0].message.content or "{}", AgentDirective
            )
            self.directives.append(directive)

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
        """Inject or exclude context paths from the generated directives."""
        if not include_paths and not exclude_paths:
            return directives

        includes = include_paths or []
        excludes = set(exclude_paths or [])
        transformed: list[AgentDirective] = []

        for directive in directives:
            new_targets = [
                t for t in directive.context_targets if t.target_identifier not in excludes
            ]
            ids = {t.target_identifier for t in new_targets}
            new_targets.extend(
                [
                    ContextTarget(
                        provider_name="file",
                        target_identifier=p,
                        is_required=True,
                        resolution_mode=TargetResolutionMode.FULL_SOURCE,
                    )
                    for p in includes
                    if p not in ids
                ]
            )
            transformed.append(directive.model_copy(update={"context_targets": new_targets}))

        return transformed

    def save_plan(self, path: str | Path) -> None:
        """Save the generated plan to disk as a JSON file."""
        file_path = Path(path).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        json_data = [d.model_dump() for d in self.directives]
        file_path.write_text(json.dumps(json_data, indent=2))
