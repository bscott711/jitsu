"""Tests for the file state provider."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jitsu.providers.file import FileStateProvider


@pytest.mark.asyncio
@patch("jitsu.providers.file.root")
async def test_file_provider_success(mock_root: MagicMock, tmp_path: Path) -> None:
    """Test successful resolution of a file."""
    mock_root.return_value = tmp_path
    target_file = tmp_path / "test.py"
    target_file.write_text("print('hello jitsu')", encoding="utf-8")

    provider = FileStateProvider()
    res = await provider.resolve("test.py")

    assert "print('hello jitsu')" in res
    assert "### File: test.py" in res


@pytest.mark.asyncio
@patch("jitsu.providers.file.root")
async def test_file_provider_not_exist(mock_root: MagicMock, tmp_path: Path) -> None:
    """Test resolution when the file does not exist."""
    mock_root.return_value = tmp_path
    provider = FileStateProvider()
    res = await provider.resolve("missing.py")
    assert "ERROR: File 'missing.py' does not exist" in res


@pytest.mark.asyncio
@patch("jitsu.providers.file.root")
async def test_file_provider_is_dir(mock_root: MagicMock, tmp_path: Path) -> None:
    """Test resolution when the target is a directory, not a file."""
    mock_root.return_value = tmp_path
    (tmp_path / "src").mkdir()

    provider = FileStateProvider()
    res = await provider.resolve("src")
    assert "ERROR: Target 'src' is not a file" in res


@pytest.mark.asyncio
@patch("jitsu.providers.file.root")
async def test_file_provider_read_error(mock_root: MagicMock, tmp_path: Path) -> None:
    """Test resolution when the file exists but cannot be read."""
    mock_root.return_value = tmp_path
    target_file = tmp_path / "test.py"
    target_file.touch()

    with patch.object(Path, "read_text", side_effect=PermissionError("Access Denied")):
        provider = FileStateProvider()
        res = await provider.resolve("test.py")
        assert "ERROR: Failed to read 'test.py'" in res
        assert "Access Denied" in res
