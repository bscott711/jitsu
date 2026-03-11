"""Tests for the file state provider."""

from pathlib import Path
from unittest.mock import patch

import pytest

from jitsu.providers.file import FileStateProvider


@pytest.mark.asyncio
async def test_file_provider_success(tmp_path: Path) -> None:
    """Test successful resolution of a file."""
    target_file = tmp_path / "test.py"
    target_file.write_text("print('hello jitsu')", encoding="utf-8")

    provider = FileStateProvider(tmp_path)
    res = await provider.resolve("test.py")

    assert "print('hello jitsu')" in res
    assert "### File: test.py" in res


@pytest.mark.asyncio
async def test_file_provider_not_exist(tmp_path: Path) -> None:
    """Test resolution when the file does not exist."""
    provider = FileStateProvider(tmp_path)
    res = await provider.resolve("missing.py")
    assert "ERROR: File 'missing.py' does not exist" in res


@pytest.mark.asyncio
async def test_file_provider_is_dir(tmp_path: Path) -> None:
    """Test resolution when the target is a directory, not a file."""
    (tmp_path / "src").mkdir()

    provider = FileStateProvider(tmp_path)
    res = await provider.resolve("src")
    assert "ERROR: Target 'src' is not a file" in res


@pytest.mark.asyncio
async def test_file_provider_read_error(tmp_path: Path) -> None:
    """Test resolution when the file exists but cannot be read."""
    target_file = tmp_path / "test.py"
    target_file.touch()

    with patch.object(Path, "read_text", side_effect=PermissionError("Access Denied")):
        provider = FileStateProvider(tmp_path)
        res = await provider.resolve("test.py")
        assert "ERROR: Failed to read 'test.py'" in res
        assert "Access Denied" in res
