"""Markdown AST context provider for Jitsu."""

from jitsu.providers.base import BaseProvider
from jitsu.utils import root

PROVIDER_NAME = "markdown_ast"


class MarkdownASTProvider(BaseProvider):
    """
    Provides a structural representation of a Markdown file.

    It collects only headings and code block delimiters to provide a high-level
    overview of the file structure.
    """

    @property
    def name(self) -> str:
        """The unique name of this provider."""
        return PROVIDER_NAME

    def read(self, target: str) -> list[str]:
        """
        Read the markdown file and collect headings and code block delimiters.

        Args:
            target: The path to the markdown file relative to project root.

        Returns:
            list[str]: The collected lines.

        """
        target_path = root() / target
        if not target_path.exists() or not target_path.is_file():
            return []

        ast_lines: list[str] = []
        try:
            with target_path.open("r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    # Heading: starts with one or more # followed by a space
                    if stripped.startswith("#"):
                        parts = stripped.split(" ", 1)
                        if len(parts) > 1 and all(c == "#" for c in parts[0]):
                            ast_lines.append(line.rstrip())
                            continue

                    # Code block delimiter: starts with exactly three backticks
                    if stripped.startswith("```") and not stripped.startswith("````"):
                        ast_lines.append(line.rstrip())
        except Exception:  # noqa: BLE001
            return []

        return ast_lines

    async def resolve(self, target: str) -> str:
        """
        Resolve the markdown structure and return it as a string.

        Args:
            target: The path to the markdown file relative to project root.

        Returns:
            str: The resolved, LLM-optimized context string.

        """
        ast_lines = self.read(target)

        if not ast_lines:
            target_path = root() / target
            if not target_path.exists():
                return f"### [FAILED] {target}\nFile not found."
            return f"### {target} (Markdown AST)\n*No headings or code blocks found.*"

        content = "\n".join(ast_lines)
        return f"### File: {target} (Markdown AST)\n```markdown\n{content}\n```"


__all__ = ["MarkdownASTProvider"]
