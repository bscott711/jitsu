"""JIT Context Compiler for weaving directives and codebase state."""

from jitsu.models.core import AgentDirective, TargetResolutionMode
from jitsu.providers import (
    ASTProvider,
    BaseProvider,
    DirectoryTreeProvider,
    EnvVarProvider,
    FileStateProvider,
    GitProvider,
    PydanticProvider,
)
from jitsu.utils.logger import get_logger

logger = get_logger(__name__)


class ContextCompiler:
    """Compiles AgentDirectives into highly-contextualized Markdown prompts."""

    def __init__(self) -> None:
        """Initialize the compiler with registered providers."""
        file_provider = FileStateProvider()
        pydantic_provider = PydanticProvider()
        ast_provider = ASTProvider()
        tree_provider = DirectoryTreeProvider()
        git_provider = GitProvider()
        env_provider = EnvVarProvider()

        self._providers: dict[str, BaseProvider] = {
            file_provider.name: file_provider,
            pydantic_provider.name: pydantic_provider,
            ast_provider.name: ast_provider,
            tree_provider.name: tree_provider,
            git_provider.name: git_provider,
            env_provider.name: env_provider,
        }

    async def compile_directive(self, directive: AgentDirective) -> str:
        """Weave the directive and live context into a single Markdown payload."""
        payload_parts = [
            f"# Jitsu Phase Directive: {directive.phase_id}",
            f"**Epic:** {directive.epic_id}",
            f"**Module Scope:** {directive.module_scope}",
            "\n## Instructions",
            directive.instructions,
        ]

        if directive.anti_patterns:
            payload_parts.append("\n## Anti-Patterns (STRICTLY FORBIDDEN)")
            payload_parts.extend([f"- {pattern}" for pattern in directive.anti_patterns])

        # Inject Definition of Done (DoD)
        payload_parts.append("\n## Definition of Done")

        if directive.completion_criteria:
            payload_parts.append("### Completion Criteria")
            payload_parts.extend(
                [f"- [ ] {criterion}" for criterion in directive.completion_criteria]
            )

        payload_parts.append("### Verification")

        if directive.verification_commands:
            payload_parts.append("You MUST run the following commands to verify your work:")
            payload_parts.extend(
                [f"```bash\n{cmd}\n```" for cmd in directive.verification_commands]
            )
        else:
            payload_parts.append("*No specific verification commands required for this phase.*")

        payload_parts.append("\n## JIT Context")
        manifest_lines: list[str] = []

        if not directive.context_targets:
            payload_parts.append("*No specific context targets requested for this phase.*")
        else:
            for target in directive.context_targets:
                # AST-First Policy for AUTO mode
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
                        payload_parts.append(f"### [FAILED] {target.target_identifier}\n{msg}")
                    manifest_lines.append(f"- `{target.target_identifier}`: **FAILED**")
                    continue

                payload_parts.append(context_data)
                payload_parts.append("---")

                # Summarize for the manifest
                summary = self._get_manifest_summary(provider_used)
                manifest_lines.append(
                    f"- `{target.target_identifier}`: **{summary}** ({provider_used})"
                )

        # Emit Compiled Context Manifest
        if manifest_lines:
            payload_parts.append("\n## Compiled Context Manifest")
            payload_parts.extend(manifest_lines)

        return "\n".join(payload_parts)

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
        }.get(provider_name, "Included")
