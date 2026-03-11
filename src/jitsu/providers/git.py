"""Git context provider for Jitsu."""

import subprocess

from jitsu.providers.base import BaseProvider


class GitProvider(BaseProvider):
    """Provides git-related context (diffs, status) of the current repository."""

    @property
    def name(self) -> str:
        """The unique name of this provider."""
        return "git"

    def _run_git(self, args: list[str]) -> str:
        """
        Execute a git command and return its output.

        Args:
            args: The git command arguments.

        Returns:
            str: The output of the git command or an error message.

        """
        try:
            result = subprocess.run(  # noqa: S603
                ["git", *args],  # noqa: S607
                capture_output=True,
                text=True,
                check=True,
                shell=False,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"ERROR: Git command failed with exit code {e.returncode}: {e.stderr}"
        except FileNotFoundError:
            return "ERROR: git command not found."
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Failed to execute git command: {e}"

    async def resolve(self, target: str) -> str:
        """
        Resolve git context into a markdown string.

        Args:
            target: The target identifier ('status', 'diff', or a specific ref).

        Returns:
            str: The resolved context string.

        """
        if target == "status":
            output = self._run_git(["status", "--short"])
            return f"### Git Status\n```text\n{output}\n```"

        # Default to diff
        diff_target = target if target and target != "diff" else "HEAD"
        output = self._run_git(["diff", diff_target])
        return f"### Git Diff: {diff_target}\n```diff\n{output}\n```"
