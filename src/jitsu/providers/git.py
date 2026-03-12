"""Git context provider for Jitsu."""

import shutil
import subprocess

from jitsu.providers.base import BaseProvider


class GitError(Exception):
    """Raised when a git command fails."""


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
            str: The output of the git command.

        Raises:
            GitError: If the git command fails or git is not installed.

        """
        try:
            git_path = shutil.which("git") or "git"
            result = subprocess.run(
                [git_path, *args],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=True,
                shell=False,
            )
        except subprocess.CalledProcessError as e:
            error_msg = f"Git command failed with exit code {e.returncode}: {e.stderr or e.stdout}"
            raise GitError(error_msg) from e
        except FileNotFoundError as e:
            error_msg = "git command not found."
            raise GitError(error_msg) from e
        else:
            return result.stdout.strip()

    async def resolve(self, target: str) -> str:
        """
        Resolve git context into a markdown string.

        Args:
            target: The target identifier ('status', 'diff', or a specific ref).

        Returns:
            str: The resolved context string.

        """
        try:
            if target == "status":
                header = "### Git Status"
                code_type = "text"
                args = ["status", "--short"]
            else:
                diff_target = target if target and target != "diff" else "HEAD"
                header = f"### Git Diff: {diff_target}"
                code_type = "diff"
                args = ["diff", diff_target]

            output = self._run_git(args)
        except GitError as e:
            return f"ERROR: {e}"
        else:
            return f"{header}\n```{code_type}\n{output}\n```"

    def get_current_branch(self) -> str:
        """
        Get the name of the current git branch.

        Returns:
            str: The name of the current branch.

        Raises:
            GitError: If the command fails.

        """
        return self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])

    def create_and_checkout_branch(self, name: str) -> None:
        """
        Create a new branch and check it out.

        Args:
            name: The name of the new branch.

        Raises:
            GitError: If the command fails.

        """
        self._run_git(["checkout", "-b", name])

    def checkout_branch(self, name: str) -> None:
        """
        Check out an existing branch.

        Args:
            name: The name of the branch to check out.

        Raises:
            GitError: If the command fails.

        """
        self._run_git(["checkout", name])

    def merge_branch(self, source: str, target: str) -> None:
        """
        Merge a source branch into a target branch.

        Args:
            source: The name of the source branch.
            target: The name of the target branch.

        Raises:
            GitError: If the command fails.

        """
        self.checkout_branch(target)
        self._run_git(["merge", source])

    def delete_branch(self, name: str) -> None:
        """
        Delete a git branch.

        Args:
            name: The name of the branch to delete.

        Raises:
            GitError: If the command fails.

        """
        self._run_git(["branch", "-d", name])
