"""File state context provider for Jitsu."""

from jitsu.providers.base import BaseProvider


class FileStateProvider(BaseProvider):
    """Provides the raw text content of a file."""

    @property
    def name(self) -> str:
        """The unique name of this provider."""
        return "file"

    async def resolve(self, target: str) -> str:
        """Resolve the file path and return its contents."""
        target_path = self.workspace_root / target

        if not target_path.exists():
            return f"ERROR: File '{target}' does not exist in the current workspace."

        if not target_path.is_file():
            return f"ERROR: Target '{target}' is not a file."

        try:
            content = target_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return f"ERROR: Failed to read '{target}': {e}"
        else:
            return f"### File: {target}\n```python\n{content}\n```"
