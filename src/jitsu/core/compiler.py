"""JIT Context Compiler for weaving directives and codebase state."""

import asyncio
from pathlib import Path

from jitsu.models.core import AgentDirective, ContextTarget, TargetResolutionMode
from jitsu.prompts import (
    TAG_CONTEXT_DETAIL,
    TAG_CONTEXT_MANIFEST,
    TAG_INSTRUCTIONS,
    TAG_PRIORITY_RECAP,
    TAG_TASK_SPEC,
    VERIFICATION_RULE,
)
from jitsu.providers import BaseProvider, ProviderRegistry
from jitsu.utils.logger import get_logger

logger = get_logger(__name__)


class ContextCompiler:
    """Compiles AgentDirectives into highly-contextualized Markdown prompts."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        """Initialize the compiler with registered providers."""
        self.workspace_root = workspace_root or Path.cwd()
        self.providers: dict[str, BaseProvider] = {
            name: cls(self.workspace_root) for name, cls in ProviderRegistry.items()
        }
        # LRU-style cache for resolved targets: (target_id, provider, mode) -> content
        self._resolution_cache: dict[tuple[str, str, TargetResolutionMode], str] = {}

    @staticmethod
    def _build_preamble(directive: AgentDirective) -> list[str]:
        """Build the static markdown headers and instructions."""
        parts: list[str] = [
            f"# Jitsu Phase Directive: {directive.phase_id}",
            f"**Epic:** {directive.epic_id}",
            f"**Module Scope:** {directive.module_scope}",
            "\n## Instructions",
            directive.instructions,
        ]

        if directive.anti_patterns:
            parts.append("\n## Anti-Patterns (STRICTLY FORBIDDEN)")
            parts.extend([f"- {pattern}" for pattern in directive.anti_patterns])

        parts.append("\n## Definition of Done")
        if directive.completion_criteria:
            parts.append("### Completion Criteria")
            parts.extend([f"- [ ] {criterion}" for criterion in directive.completion_criteria])

        parts.append("### Verification")
        if directive.verification_commands:
            parts.append("You MUST run the following commands to verify your work:")
            parts.extend([f"```bash\n{cmd}\n```" for cmd in directive.verification_commands])
        else:
            parts.append("*No specific verification commands required for this phase.*")

        return parts

    async def _resolve_single_target(self, target: ContextTarget) -> tuple[str, str]:
        """Resolve a single target with proper mode handling."""
        if target.resolution_mode == TargetResolutionMode.AUTO:
            return await self.resolve_auto(target.target_identifier, target.provider_name)
        return await self.resolve_explicit(target.target_identifier, target.resolution_mode)

    async def _resolve_targets(self, targets: list[ContextTarget]) -> tuple[list[str], list[str]]:
        """Process context targets and build the manifest."""
        if not targets:
            return [], []

        # Resolve all targets concurrently
        tasks = [self._resolve_single_target(target) for target in targets]
        results: list[tuple[str, str]] = await asyncio.gather(*tasks)

        parts: list[str] = []
        manifest: list[str] = []

        for target, (context_data, provider_used) in zip(targets, results, strict=True):
            if provider_used == "none":
                msg = (
                    f"**Warning:** Unknown provider '{target.provider_name}' or "
                    f"resolution failed for '{target.target_identifier}'. "
                )
                if target.is_required:
                    parts.append(f"### [FAILED] {target.target_identifier}\n{msg}")
                manifest.append(f"- `{target.target_identifier}`: **FAILED**")
                continue

            parts.extend([context_data, "---"])
            summary = self._get_manifest_summary(provider_used)
            manifest.append(f"- `{target.target_identifier}`: **{summary}** ({provider_used})")

        return parts, manifest

    async def compile_directive(self, directive: AgentDirective) -> str:
        """Weave the directive and live context into a single U-Curve XML payload."""
        # 1. Instructions
        preamble_parts = self._build_preamble(directive)
        instructions_content = "\n".join(preamble_parts)

        # 2 & 3. Context
        target_parts: list[str] = []
        manifest_lines: list[str] = []
        if directive.context_targets:
            target_parts, manifest_lines = await self._resolve_targets(directive.context_targets)

        manifest_content = "\n".join(manifest_lines) if manifest_lines else "No context targets."
        detail_content = "\n".join(target_parts) if target_parts else "No context details."

        # Compile U-Curve Payload
        payload: list[str] = [
            f"{TAG_INSTRUCTIONS}\n{instructions_content}\n{TAG_INSTRUCTIONS.replace('<', '</')}",
            f"{TAG_CONTEXT_MANIFEST}\n{manifest_content}\n{TAG_CONTEXT_MANIFEST.replace('<', '</')}",
            f"{TAG_CONTEXT_DETAIL}\n{detail_content}\n{TAG_CONTEXT_DETAIL.replace('<', '</')}",
            f"{TAG_PRIORITY_RECAP}\n{VERIFICATION_RULE}\n{TAG_PRIORITY_RECAP.replace('<', '</')}",
            (
                f"{TAG_TASK_SPEC}\n"
                "Please provide the file edits to fulfill the directive above while  "
                "adhering to all constraints.\n"
                f"{TAG_TASK_SPEC.replace('<', '</')}"
            ),
        ]

        return "\n\n".join(payload)

    def _get_resolution_priority(
        self, target_id: str, preferred_provider: str
    ) -> list[tuple[str, bool]]:
        """
        Build ordered list of (provider_name, should_try) tuples.

        Returns providers in priority order with boolean indicating if condition is met.
        """
        is_python_file = target_id.endswith(".py") or "/" in target_id
        is_symbol = "." in target_id
        is_custom_provider = preferred_provider not in ("ast", "pydantic", "file", "tree")

        return [
            ("ast", is_python_file),
            ("pydantic", is_symbol),
            (preferred_provider, is_custom_provider),
            ("tree", True),  # Always try tree
            ("file", True),  # Always try file as fallback
        ]

    async def _try_resolve_with_priority(
        self,
        target_id: str,
        cache_key: tuple[str, str, TargetResolutionMode],
        priority_list: list[tuple[str, bool]],
    ) -> tuple[str, str]:
        """
        Try providers in priority order until one succeeds.

        Returns (content, provider_name) or ("", "none") if all fail.
        """
        for provider_name, should_try in priority_list:
            if not should_try:
                continue

            res = await self._try_resolve(provider_name, target_id)
            if res:
                self._resolution_cache[cache_key] = res
                return res, provider_name

            # Log warning only for custom unknown providers
            if provider_name not in ("ast", "pydantic", "file", "tree"):
                logger.warning("Unknown provider '%s' requested", provider_name)

        logger.error("All providers failed to resolve target: %s", target_id)
        return "", "none"

    async def resolve_auto(self, target_id: str, preferred_provider: str) -> tuple[str, str]:
        """Attempt to resolve target: AST -> Pydantic -> Preferred -> FileState."""
        # Check cache first
        cache_key = (target_id, preferred_provider, TargetResolutionMode.AUTO)
        if cache_key in self._resolution_cache:
            cached = self._resolution_cache[cache_key]
            if not cached.startswith(("### [FAILED] ", "ERROR: ")):
                return cached, preferred_provider

        # Build priority list and try providers in order
        priority_list = self._get_resolution_priority(target_id, preferred_provider)
        return await self._try_resolve_with_priority(target_id, cache_key, priority_list)

    async def _try_resolve(self, provider_name: str, target_id: str) -> str | None:
        """Attempt to resolve with a specific provider, returning None on failure."""
        provider = self.providers.get(provider_name)
        if not provider:
            return None
        res = await provider.resolve(target_id)
        if res.startswith(("### [FAILED] ", "ERROR: ")):
            return None
        return res

    async def resolve_explicit(self, target_id: str, mode: TargetResolutionMode) -> tuple[str, str]:
        """Resolve target using an explicit mode."""
        provider_name_map: dict[TargetResolutionMode, str] = {
            TargetResolutionMode.STRUCTURE_ONLY: "ast",
            TargetResolutionMode.SCHEMA_ONLY: "pydantic",
            TargetResolutionMode.FULL_SOURCE: "file",
        }
        provider_name = provider_name_map.get(mode)

        if not provider_name:
            logger.error("Unknown resolution mode provided: %s", mode)
            return "", "none"

        provider = self.providers.get(provider_name)
        if not provider:
            logger.error("Provider '%s' not found for mode '%s'", provider_name, mode)
            return "", "none"

        res = await provider.resolve(target_id)
        if res.startswith(("### [FAILED] ", "ERROR: ")):
            return res, "none"

        return res, provider_name

    def _get_manifest_summary(self, provider_name: str) -> str:
        """Map provider name to a human-readable manifest summary."""
        summary_map: dict[str, str] = {
            "ast": "Summarized (Structural AST)",
            "pydantic": "Condensed (JSON Schema)",
            "file": "Full Source",
            "tree": "Visual Tree Structure",
            "git": "Git Repository State",
            "env_var": "Environment Variable",
            "markdown_ast": "Markdown Structure (AST)",
        }
        return summary_map.get(provider_name, "Included")

    def clear_caches(self) -> None:
        """Clear internal caches. Useful for testing or memory management."""
        self._resolution_cache.clear()
