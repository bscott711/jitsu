"""Tests for the GitProvider."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jitsu.providers.git import GitError, GitProvider


@pytest.mark.asyncio
async def test_git_provider_name() -> None:
    """Test the provider name."""
    provider = GitProvider(Path.cwd())
    assert provider.name == "git"


@pytest.mark.asyncio
async def test_git_provider_resolve_diff() -> None:
    """Test successful git diff resolution."""
    provider = GitProvider(Path.cwd())
    mock_output = "diff --git a/file.py b/file.py\n+new line"

    mock_result = MagicMock()
    mock_result.stdout = mock_output

    with patch("jitsu.providers.git.subprocess.run", return_value=mock_result):
        resolved = await provider.resolve("HEAD")
        assert "### Git Diff: HEAD" in resolved
        assert mock_output in resolved


@pytest.mark.asyncio
async def test_git_provider_resolve_status() -> None:
    """Test successful git status resolution."""
    provider = GitProvider(Path.cwd())
    mock_output = "M  src/main.py\n?? tests/test.py"

    mock_result = MagicMock()
    mock_result.stdout = mock_output

    with patch("jitsu.providers.git.subprocess.run", return_value=mock_result):
        resolved = await provider.resolve("status")
        assert "### Git Status" in resolved
        assert mock_output in resolved


@pytest.mark.asyncio
async def test_git_provider_called_process_error() -> None:
    """Test handling of CalledProcessError."""
    provider = GitProvider(Path.cwd())
    error = subprocess.CalledProcessError(
        returncode=128, cmd=["git", "diff", "HEAD"], stderr="not a git repo"
    )

    with patch("jitsu.providers.git.subprocess.run", side_effect=error):
        resolved = await provider.resolve("HEAD")
        assert "ERROR: Git command failed with exit code 128" in resolved
        assert "not a git repo" in resolved


@pytest.mark.asyncio
async def test_git_provider_file_not_found() -> None:
    """Test handling of FileNotFoundError (git not installed)."""
    provider = GitProvider(Path.cwd())

    with patch("jitsu.providers.git.subprocess.run", side_effect=FileNotFoundError):
        resolved = await provider.resolve("HEAD")
        assert "ERROR: git command not found." in resolved


def test_git_get_current_branch() -> None:
    """Test get_current_branch success."""
    provider = GitProvider(Path.cwd())
    mock_result = MagicMock()
    mock_result.stdout = "main\n"

    with patch("jitsu.providers.git.subprocess.run", return_value=mock_result):
        assert provider.get_current_branch() == "main"


def test_git_create_and_checkout_branch() -> None:
    """Test create_and_checkout_branch success."""
    provider = GitProvider(Path.cwd())
    mock_result = MagicMock()
    mock_result.stdout = ""

    with patch("jitsu.providers.git.subprocess.run", return_value=mock_result) as mock_run:
        provider.create_and_checkout_branch("feature-x")
        mock_run.assert_called_once()
        args, _kwargs = mock_run.call_args
        assert "checkout" in args[0]
        assert "-b" in args[0]
        assert "feature-x" in args[0]


def test_git_checkout_branch() -> None:
    """Test checkout_branch success."""
    provider = GitProvider(Path.cwd())
    mock_result = MagicMock()
    mock_result.stdout = ""

    with patch("jitsu.providers.git.subprocess.run", return_value=mock_result) as mock_run:
        provider.checkout_branch("main")
        mock_run.assert_called_once()
        args, _kwargs = mock_run.call_args
        assert "checkout" in args[0]
        assert "main" in args[0]
        assert "-b" not in args[0]


def test_git_merge_branch() -> None:
    """Test merge_branch success (includes implicit checkout)."""
    provider = GitProvider(Path.cwd())
    mock_result = MagicMock()
    mock_result.stdout = "Already up to date."

    with patch("jitsu.providers.git.subprocess.run", return_value=mock_result) as mock_run:
        provider.merge_branch("feature", "main")
        expected_call_count = 2
        assert mock_run.call_count == expected_call_count
        # First call: checkout main
        assert "checkout" in mock_run.call_args_list[0][0][0]
        assert "main" in mock_run.call_args_list[0][0][0]
        # Second call: merge feature
        assert "merge" in mock_run.call_args_list[1][0][0]
        assert "feature" in mock_run.call_args_list[1][0][0]


def test_git_delete_branch() -> None:
    """Test delete_branch success."""
    provider = GitProvider(Path.cwd())
    mock_result = MagicMock()
    mock_result.stdout = "Deleted branch feature-x."

    with patch("jitsu.providers.git.subprocess.run", return_value=mock_result) as mock_run:
        provider.delete_branch("feature-x")
        mock_run.assert_called_once()
        assert "branch" in mock_run.call_args[0][0]
        assert "-d" in mock_run.call_args[0][0]
        assert "feature-x" in mock_run.call_args[0][0]


def test_git_error_mapping() -> None:
    """Test that CalledProcessError is correctly mapped to GitError."""
    provider = GitProvider(Path.cwd())
    error = subprocess.CalledProcessError(
        returncode=1, cmd=["git", "status"], stderr="something went wrong"
    )

    with patch("jitsu.providers.git.subprocess.run", side_effect=error):
        with pytest.raises(GitError) as exc:
            provider.get_current_branch()
        assert "Git command failed with exit code 1" in str(exc.value)
        assert "something went wrong" in str(exc.value)


def test_git_not_found_error() -> None:
    """Test that FileNotFoundError is correctly mapped to GitError."""
    provider = GitProvider(Path.cwd())

    with patch("jitsu.providers.git.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(GitError) as exc:
            provider.get_current_branch()
        assert "git command not found." in str(exc.value)
