"""Generates a sequence of AgentDirectives using an LLM."""

import asyncio
import inspect
import json
import logging
import re
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, get_args

import anyio
import typer
from openai import AsyncOpenAI

from jitsu.config import settings
from jitsu.core.client import LLMClientFactory
from jitsu.models.core import (
    AgentDirective,
    ContextTarget,
    EpicBlueprint,
    PhaseBlueprint,
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


class JitsuFuzzyParser:
    """Extracts structured data safely from XML-tagged LLM output."""

    @staticmethod
    def extract_tag(text: str, tag: str, default: str = "") -> str:
        """Extract content from an XML-like tag, handling missing closing tags."""
        pattern = rf"<{tag}>(.*?)(?:</{tag}>|<(?=[a-zA-Z_]+>)|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else default

    @classmethod
    def parse_blueprint(cls, text: str) -> EpicBlueprint:
        """Extract the macro blueprint."""
        epic_id = cls.extract_tag(text, "epic_id", f"epic-{uuid.uuid4().hex[:6]}")
        phases = []
        phase_blocks = re.findall(r"<phase>(.*?)</phase>", text, re.IGNORECASE | re.DOTALL)

        for block in phase_blocks:
            pid = cls.extract_tag(block, "phase_id")
            desc = cls.extract_tag(block, "description")
            if pid:
                phases.append(PhaseBlueprint(phase_id=pid, description=desc))

        return EpicBlueprint(epic_id=epic_id, phases=phases)

    @classmethod
    def parse_directive(cls, text: str, epic_id: str, phase_id: str) -> AgentDirective:
        """Extract the micro directive."""
        scope_raw = cls.extract_tag(text, "module_scope")
        scope_list = [s.strip() for s in scope_raw.split(",")] if scope_raw else []

        targets_raw = cls.extract_tag(text, "context_targets")
        target_list = [t.strip() for t in targets_raw.split("\n") if t.strip()]

        context_targets = [
            ContextTarget(
                provider_name="file",
                target_identifier=t,
                is_required=True,
                resolution_mode=TargetResolutionMode.FULL_SOURCE,
            )
            for t in target_list
        ]

        anti_patterns = [
            a.strip().lstrip("-* ")
            for a in cls.extract_tag(text, "anti_patterns").split("\n")
            if a.strip()
        ]
        verification = [
            v.strip()
            for v in cls.extract_tag(text, "verification_commands").split("\n")
            if v.strip()
        ]
        completion = [
            c.strip().lstrip("-* ")
            for c in cls.extract_tag(text, "completion_criteria").split("\n")
            if c.strip()
        ]

        return AgentDirective(
            epic_id=epic_id,
            phase_id=phase_id,
            module_scope=scope_list,
            instructions=cls.extract_tag(text, "instructions", "No instructions provided."),
            context_targets=context_targets,
            anti_patterns=anti_patterns,
            verification_commands=verification,
            completion_criteria=completion,
        )


class JitsuPlanner:
    """Generates a sequence of AgentDirectives using an LLM."""

    def __init__(
        self,
        objective: str,
        relevant_files: list[str],
        client: AsyncOpenAI | None = None,
        on_status: PlannerStatusCallback | None = None,
    ) -> None:
        """Initialize the planner with an objective and context."""
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

    async def _elaborate_phase(
        self,
        index: int,
        phase: PhaseBlueprint,
        blueprint: EpicBlueprint,
        base_prompt: str,
        user_message: str,
        allowed_providers: str,
        _model: str,
        client: AsyncOpenAI,
        opts: PlannerOptions,
    ) -> AgentDirective:
        """Elaborate a single phase concurrently."""
        progress = 40.0 + (50.0 * (index / max(1, len(blueprint.phases))))
        await self._emit_status(
            PlannerStage.DRAFTING_PHASES,
            f"Elaborating Phase {index + 1} ({phase.phase_id})...",
            progress,
            opts.on_progress,
            opts.on_status,
        )

        phase_prompt = (
            base_prompt
            + PLANNER_MICRO_PROMPT.format(
                epic_id=blueprint.epic_id,
                phase_id=phase.phase_id,
                phase_description=phase.description,
                allowed_providers=allowed_providers,
            )
            + f"\n{VERIFICATION_RULE}\n\n{TOOLCHAIN_CONSTRAINTS}\n"
        )

        response = await client.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": phase_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        # FIX: Access choices[0].message.content (not choices.message)
        content = response.choices[0].message.content or ""
        return JitsuFuzzyParser.parse_directive(content, blueprint.epic_id, phase.phase_id)

    async def generate_plan(
        self,
        options: PlannerOptions | None = None,
    ) -> list[AgentDirective]:
        """Query the LLM and generate a validated list of directives using parallel passes."""
        opts = options or PlannerOptions()
        _model = opts.model or settings.planner_model

        if self._client is not None:
            client = self._client
        else:
            factory_client = LLMClientFactory.create()
            client = factory_client.client if hasattr(factory_client, "client") else factory_client

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

        blueprint_resp = await client.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": base_system_prompt + PLANNER_MACRO_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )

        # FIX: Access choices[0].message.content (not choices.message)
        content = blueprint_resp.choices[0].message.content or ""
        blueprint = JitsuFuzzyParser.parse_blueprint(content)
        self.epic_id = blueprint.epic_id

        if opts.verbose:
            typer.secho("\n[DEBUG] Epic Blueprint:", fg=typer.colors.YELLOW, bold=True, err=True)
            typer.secho(blueprint.model_dump_json(indent=2), fg=typer.colors.YELLOW, err=True)

        await self._emit_status(
            PlannerStage.ANALYZING_SCOPE,
            "Drafting phases...",
            40.0,
            opts.on_progress,
            opts.on_status,
        )

        # Pass 2: Micro - Elaborate phases in parallel
        tasks = [
            self._elaborate_phase(
                i,
                phase,
                blueprint,
                base_system_prompt,
                user_message,
                allowed_providers,
                _model,
                client,
                opts,
            )
            for i, phase in enumerate(blueprint.phases)
        ]
        self.directives = list(await asyncio.gather(*tasks))

        await self._emit_status(
            PlannerStage.VALIDATING_SCHEMA,
            "Finalizing scope...",
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
        """Inject or exclude context paths from the generated directives."""
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
        """Save the generated plan to disk as a JSON file."""
        file_path = Path(path).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        json_data = [d.model_dump() for d in self.directives]
        file_path.write_text(json.dumps(json_data, indent=2))
