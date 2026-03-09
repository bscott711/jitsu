"""JIT Context Compiler for weaving directives and codebase state."""

from jitsu.models.core import AgentDirective
from jitsu.providers.base import BaseProvider
from jitsu.providers.file import FileStateProvider
from jitsu.providers.pydantic import PydanticV2Provider


class ContextCompiler:
    """Compiles AgentDirectives into highly-contextualized Markdown prompts."""

    def __init__(self) -> None:
        """Initialize the compiler with registered providers."""
        file_provider = FileStateProvider()
        pydantic_provider = PydanticV2Provider()
        self._providers: dict[str, BaseProvider] = {
            file_provider.name: file_provider,
            pydantic_provider.name: pydantic_provider,
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

        payload_parts.append("\n## JIT Context")
        if not directive.context_targets:
            payload_parts.append("*No specific context targets requested for this phase.*")
        else:
            for target in directive.context_targets:
                provider = self._providers.get(target.provider_name)
                if not provider:
                    msg = f"**Warning:** Unknown provider '{target.provider_name}' requested for '{target.target_identifier}'."
                    if target.is_required:
                        payload_parts.append(f"### [FAILED] {target.target_identifier}\n{msg}")
                    continue

                # MUST be awaited because provider.resolve() is an async coroutine
                context_data = await provider.resolve(target.target_identifier)
                payload_parts.append(context_data)
                payload_parts.append("---")

        return "\n".join(payload_parts)
