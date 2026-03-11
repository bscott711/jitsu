"""Git Diff context provider for Jitsu."""

import subprocess

from jitsu.providers.base import BaseProvider


class GitDiffProvider(BaseProvider):
    """Provides the git diff of the current repository."""

    def __init__(self, command: list[str] | None = None) -> None:
        """
        Initialize the provider with an optional command.

        Args:
            command: The git command to execute. Defaults to ["git", "diff", "HEAD"].

        """
        self._command = command or ["git", "diff", "HEAD"]

    @property
    def name(self) -> str:
        """The unique name of this provider."""
        return "git_diff"

    def fetch_content(self) -> str:
        """
        Execute git diff HEAD using subprocess and return the output.

        Returns:
            str: The output of the git diff command or an error message.

        """
        try:
            # Using text=True for string output as requested by directive
            return subprocess.check_output(self._command, text=True, stderr=subprocess.STDOUT)  # noqa: S603
        except subprocess.CalledProcessError as e:
            return f"ERROR: Git command failed with exit code {e.returncode}: {e.output}"
        except FileNotFoundError:
            return "ERROR: git command not found."
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Failed to execute git command: {e}"

    async def resolve(self, target: str) -> str:
        """
        Resolve the git diff into a context string.

        Args:
            target: The target identifier (e.g., 'HEAD' or a specific ref).

        Returns:
            str: The resolved context string.

        """
        diff_output = self.fetch_content()
        display_target = target or "HEAD"
        return f"### Git Diff: {display_target}\n```diff\n{diff_output}\n```"
