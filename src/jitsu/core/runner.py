"""Utility for running OS-level subprocesses with dynamic binary resolution."""

import shlex
import shutil
import subprocess


class CommandRunner:
    """Encapsulates subprocess calls with dynamic binary resolution."""

    @staticmethod
    def run(cmd: str, *, check: bool = False) -> subprocess.CompletedProcess[str]:
        """
        Run a shell command string, resolving binaries dynamically.

        If the command starts with a known binary alias (e.g. 'just'), the
        binary is resolved via `shutil.which` before execution.

        Args:
            cmd: The command string to execute (e.g. "just verify").
            check: If True, raises CalledProcessError on non-zero exit code.

        Returns:
            A CompletedProcess instance with stdout, stderr, and returncode.

        Raises:
            FileNotFoundError: If the binary cannot be found in PATH.
            subprocess.CalledProcessError: If check=True and the command fails.

        """
        args = shlex.split(cmd)
        binary = args[0]

        resolved = shutil.which(binary)
        if resolved is None:
            msg = f"Executable '{binary}' not found in PATH."
            raise FileNotFoundError(msg)
        args[0] = resolved

        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=check,
        )

    @staticmethod
    def run_args(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
        """
        Run a command from an explicit args list, resolving the binary dynamically.

        Args:
            args: The command and its arguments as a list.
            check: If True, raises CalledProcessError on non-zero exit code.

        Returns:
            A CompletedProcess instance.

        Raises:
            FileNotFoundError: If the binary cannot be found in PATH.
            subprocess.CalledProcessError: If check=True and the command fails.

        """
        resolved_args = list(args)
        binary = resolved_args[0]

        resolved = shutil.which(binary)
        if resolved is None:
            msg = f"Executable '{binary}' not found in PATH."
            raise FileNotFoundError(msg)
        resolved_args[0] = resolved

        return subprocess.run(
            resolved_args,
            capture_output=True,
            text=True,
            check=check,
        )
