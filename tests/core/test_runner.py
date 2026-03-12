"""Tests for the CommandRunner utility."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from jitsu.core.runner import CommandRunner


def test_run_success() -> None:
    """Test CommandRunner.run() executes a command and returns result."""
    mock_result = MagicMock(returncode=0, stdout="output", stderr="")

    with (
        patch("jitsu.core.runner.shutil.which", return_value="/usr/bin/echo"),
        patch("jitsu.core.runner.subprocess.run", return_value=mock_result) as mock_run,
    ):
        result = CommandRunner.run("echo hello")

    assert result.returncode == 0
    mock_run.assert_called_once_with(
        ["/usr/bin/echo", "hello"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_run_binary_not_found() -> None:
    """Test CommandRunner.run() raises FileNotFoundError if binary not in PATH."""
    with (
        patch("jitsu.core.runner.shutil.which", return_value=None),
        pytest.raises(FileNotFoundError, match="not found in PATH"),
    ):
        CommandRunner.run("nonexistent-binary foo")


def test_run_with_check_on_failure() -> None:
    """Test CommandRunner.run() respects check=True."""
    error = subprocess.CalledProcessError(returncode=1, cmd="just verify")

    with (
        patch("jitsu.core.runner.shutil.which", return_value="/usr/bin/just"),
        patch("jitsu.core.runner.subprocess.run", side_effect=error),
        pytest.raises(subprocess.CalledProcessError),
    ):
        CommandRunner.run("just verify", check=True)


def test_run_args_success() -> None:
    """Test CommandRunner.run_args() executes a command from an args list."""
    mock_result = MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("jitsu.core.runner.shutil.which", return_value="/opt/homebrew/bin/just"),
        patch("jitsu.core.runner.subprocess.run", return_value=mock_result) as mock_run,
    ):
        result = CommandRunner.run_args(["just", "commit", "feat: test"])

    assert result.returncode == 0
    mock_run.assert_called_once_with(
        ["/opt/homebrew/bin/just", "commit", "feat: test"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_run_args_binary_not_found() -> None:
    """Test CommandRunner.run_args() raises FileNotFoundError if binary not in PATH."""
    with (
        patch("jitsu.core.runner.shutil.which", return_value=None),
        pytest.raises(FileNotFoundError, match="not found in PATH"),
    ):
        CommandRunner.run_args(["nonexistent", "arg1"])


def test_run_args_with_check_on_failure() -> None:
    """Test CommandRunner.run_args() respects check=True."""
    error = subprocess.CalledProcessError(returncode=1, cmd="just sync")
    error.stderr = "git error"

    with (
        patch("jitsu.core.runner.shutil.which", return_value="/usr/bin/just"),
        patch("jitsu.core.runner.subprocess.run", side_effect=error),
        pytest.raises(subprocess.CalledProcessError),
    ):
        CommandRunner.run_args(["just", "sync", "feat: test"], check=True)
