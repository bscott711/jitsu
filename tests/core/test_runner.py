"""Tests for the CommandRunner utility."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from jitsu.core.runner import CommandRunner


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    """Clear CommandRunner cache before each test."""
    CommandRunner.clear_binary_cache()


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


def test_resolve_binary_caching() -> None:
    """Test that _resolve_binary caches results."""
    with patch("jitsu.core.runner.shutil.which", return_value="/usr/bin/just") as mock_which:
        # First call resolves binary
        result1 = CommandRunner._resolve_binary("just")
        assert result1 == "/usr/bin/just"
        assert mock_which.call_count == 1

        # Second call uses cache
        result2 = CommandRunner._resolve_binary("just")
        assert result2 == "/usr/bin/just"
        assert mock_which.call_count == 1  # Not called again

        # Clear cache and verify re-resolution
        CommandRunner.clear_binary_cache()
        CommandRunner._resolve_binary("just")
        num_call = 2
        assert mock_which.call_count == num_call


def test_run_uses_binary_cache() -> None:
    """Test that run() benefits from binary caching."""
    mock_result = MagicMock(returncode=0, stdout="out", stderr="")
    with (
        patch("jitsu.core.runner.shutil.which", return_value="/usr/bin/echo") as mock_which,
        patch("jitsu.core.runner.subprocess.run", return_value=mock_result) as mock_run,
    ):
        # Run same command twice
        CommandRunner.run("echo hello")
        CommandRunner.run("echo hello")

        # shutil.which should only be called once due to caching
        assert mock_which.call_count == 1
        # But subprocess.run should be called twice (actual execution)
        num_call = 2
        assert mock_run.call_count == num_call


def test_run_args_uses_binary_cache() -> None:
    """Test that run_args() benefits from binary caching."""
    mock_result = MagicMock(returncode=0, stdout="out", stderr="")
    with (
        patch("jitsu.core.runner.shutil.which", return_value="/usr/bin/git") as mock_which,
        patch("jitsu.core.runner.subprocess.run", return_value=mock_result) as mock_run,
    ):
        # Run same command twice
        CommandRunner.run_args(["git", "status"])
        CommandRunner.run_args(["git", "status"])

        # shutil.which should only be called once due to caching
        assert mock_which.call_count == 1
        # But subprocess.run should be called twice (actual execution)
        num_call = 2
        assert mock_run.call_count == num_call


def test_clear_binary_cache() -> None:
    """Test that clear_binary_cache() resets the cache."""
    with patch("jitsu.core.runner.shutil.which", return_value="/usr/bin/just"):
        # Populate cache
        CommandRunner._resolve_binary("just")
        CommandRunner._resolve_binary("git")

        # Clear cache
        CommandRunner.clear_binary_cache()

        # Cache should be empty (verified by re-calling which)
        with patch("jitsu.core.runner.shutil.which", return_value="/usr/bin/just") as mock_which:
            CommandRunner._resolve_binary("just")
            assert mock_which.call_count == 1  # Had to re-resolve
