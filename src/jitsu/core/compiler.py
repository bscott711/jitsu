"""JIT Context Compiler for weaving directives and codebase state."""

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
        self._providers: dict[str, BaseProvider] = {
            name: cls(self.workspace_root) for name, cls in ProviderRegistry.items()
        }

    @staticmethod
    def _build_preamble(directive: AgentDirective) -> list[str]:
        """Build the static markdown headers and instructions."""
        parts = [
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

    async def _resolve_targets(self, targets: list[ContextTarget]) -> tuple[list[str], list[str]]:
        """Process context targets and build the manifest."""
        parts: list[str] = []
        manifest: list[str] = []

        for target in targets:
            if target.resolution_mode == TargetResolutionMode.AUTO:
                context_data, provider_used = await self._resolve_auto(
                    target.target_identifier, target.provider_name
                )
            else:
                context_data, provider_used = await self._resolve_explicit(
                    target.target_identifier, target.resolution_mode
                )

            if provider_used == "none":
                msg = f"**Warning:** Unknown provider '{target.provider_name}' or resolution failed for '{target.target_identifier}'."
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
        target_parts = []
        manifest_lines = []
        if directive.context_targets:
            target_parts, manifest_lines = await self._resolve_targets(directive.context_targets)

        manifest_content = "\n".join(manifest_lines) if manifest_lines else "No context targets."
        detail_content = "\n".join(target_parts) if target_parts else "No context details."

        # Compile U-Curve Payload
        payload = [
            f"{TAG_INSTRUCTIONS}\n{instructions_content}\n{TAG_INSTRUCTIONS.replace('<', '</')}",
            f"{TAG_CONTEXT_MANIFEST}\n{manifest_content}\n{TAG_CONTEXT_MANIFEST.replace('<', '</')}",
            f"{TAG_CONTEXT_DETAIL}\n{detail_content}\n{TAG_CONTEXT_DETAIL.replace('<', '</')}",
            f"{TAG_PRIORITY_RECAP}\n{VERIFICATION_RULE}\n{TAG_PRIORITY_RECAP.replace('<', '</')}",
            (
                f"{TAG_TASK_SPEC}\n"
                "Please provide the file edits to fulfill the directive above while "
                "adhering to all constraints.\n"
                f"{TAG_TASK_SPEC.replace('<', '</')}"
            ),
        ]

        return "\n\n".join(payload)

    async def _resolve_auto(self, target_id: str, preferred_provider: str) -> tuple[str, str]:
        """Attempt to resolve target: AST -> Pydantic -> Preferred -> FileState."""
        # Policy: Try AST first for Python structural logic
        if target_id.endswith(".py") or "/" in target_id:
            res = await self._try_resolve("ast", target_id)
            if res:
                return res, "ast"

        # Try Pydantic if it looks like a symbol
        if "." in target_id:
            res = await self._try_resolve("pydantic", target_id)
            if res:
                return res, "pydantic"

        # Try preferred provider if it's not one we already tried
        if preferred_provider not in ("ast", "pydantic", "file", "tree"):
            res = await self._try_resolve(preferred_provider, target_id)
            if res:
                return res, preferred_provider
            logger.warning("Unknown provider '%s' requested", preferred_provider)

        # Try Directory Tree representation
        res = await self._try_resolve("tree", target_id)
        if res:
            return res, "tree"

        # Fallback to Full Source
        res = await self._try_resolve("file", target_id)
        if res:
            return res, "file"

        logger.error("All providers failed to resolve target: %s", target_id)
        return "", "none"

    async def _try_resolve(self, provider_name: str, target_id: str) -> str | None:
        """Attempt to resolve with a specific provider, returning None on failure."""
        provider = self._providers.get(provider_name)
        if not provider:
            return None
        res = await provider.resolve(target_id)
        if res.startswith(("### [FAILED]", "ERROR:")):
            return None
        return res

    async def _resolve_explicit(
        self, target_id: str, mode: TargetResolutionMode
    ) -> tuple[str, str]:
        """Resolve target using an explicit mode."""
        provider_name = {
            TargetResolutionMode.STRUCTURE_ONLY: "ast",
            TargetResolutionMode.SCHEMA_ONLY: "pydantic",
            TargetResolutionMode.FULL_SOURCE: "file",
        }.get(mode)

        if not provider_name:
            logger.error("Unknown resolution mode provided: %s", mode)
            return "", "none"

        provider = self._providers.get(provider_name)
        if not provider:
            logger.error("Provider '%s' not found for mode '%s'", provider_name, mode)
            return "", "none"

        res = await provider.resolve(target_id)
        if res.startswith(("### [FAILED]", "ERROR:")):
            return res, "none"

        return res, provider_name

    def _get_manifest_summary(self, provider_name: str) -> str:
        """Map provider name to a human-readable manifest summary."""
        return {
            "ast": "Summarized (Structural AST)",
            "pydantic": "Condensed (JSON Schema)",
            "file": "Full Source",
            "tree": "Visual Tree Structure",
            "git": "Git Repository State",
            "env_var": "Environment Variable",
            "markdown_ast": "Markdown Structure (AST)",
        }.get(provider_name, "Included")
