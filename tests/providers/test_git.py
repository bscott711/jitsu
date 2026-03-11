"""Tests for the GitDiffProvider."""

import subprocess
from unittest.mock import patch

import pytest

from jitsu.providers.git import GitDiffProvider


@pytest.mark.asyncio
async def test_git_diff_provider_name() -> None:
    """Test the provider name."""
    provider = GitDiffProvider()
    assert provider.name == "git_diff"


@pytest.mark.asyncio
async def test_git_diff_provider_success() -> None:
    """Test successful git diff execution."""
    provider = GitDiffProvider()
    mock_output = "diff --git a/file.py b/file.py\n+new line"

    with patch("jitsu.providers.git.subprocess.check_output", return_value=mock_output):
        content = provider.fetch_content()
        assert content == mock_output

        resolved = await provider.resolve("HEAD")
        assert "### Git Diff: HEAD" in resolved
        assert mock_output in resolved


@pytest.mark.asyncio
async def test_git_diff_provider_called_process_error() -> None:
    """Test handling of CalledProcessError."""
    provider = GitDiffProvider()
    error = subprocess.CalledProcessError(
        returncode=128, cmd="git diff HEAD", output="not a git repo"
    )

    with patch("jitsu.providers.git.subprocess.check_output", side_effect=error):
        content = provider.fetch_content()
        assert "ERROR: Git command failed with exit code 128" in content
        assert "not a git repo" in content


@pytest.mark.asyncio
async def test_git_diff_provider_file_not_found() -> None:
    """Test handling of FileNotFoundError (git not installed)."""
    provider = GitDiffProvider()

    with patch("jitsu.providers.git.subprocess.check_output", side_effect=FileNotFoundError):
        content = provider.fetch_content()
        assert "ERROR: git command not found." in content


@pytest.mark.asyncio
async def test_git_diff_provider_generic_exception() -> None:
    """Test handling of other exceptions."""
    provider = GitDiffProvider()

    with patch(
        "jitsu.providers.git.subprocess.check_output", side_effect=RuntimeError("unexpected")
    ):
        content = provider.fetch_content()
        assert "ERROR: Failed to execute git command: unexpected" in content


@pytest.mark.asyncio
async def test_git_diff_provider_custom_command() -> None:
    """Test provider with a custom command."""
    custom_command = ["git", "diff", "--staged"]
    provider = GitDiffProvider(command=custom_command)

    with patch("jitsu.providers.git.subprocess.check_output") as mock_check:
        mock_check.return_value = "staged changes"
        await provider.resolve("staged")
        mock_check.assert_called_once_with(custom_command, text=True, stderr=subprocess.STDOUT)
