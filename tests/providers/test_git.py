"""Tests for the GitProvider."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jitsu.providers.git import GitProvider


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
