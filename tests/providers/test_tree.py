"""Tests for the DirectoryTreeProvider."""

from pathlib import Path
from unittest.mock import patch

import pytest

from jitsu.providers.tree import DirectoryTreeProvider


@pytest.mark.asyncio
async def test_tree_provider_name() -> None:
    """Test the provider name."""
    provider = DirectoryTreeProvider(Path.cwd())
    assert provider.name == "tree"


@pytest.mark.asyncio
async def test_tree_provider_resolve_success(tmp_path: Path) -> None:
    """Test successful directory tree generation."""
    # Create structure:
    # tmp_path/
    #   dir1/
    #     sub1/
    #       file1.txt
    #     file2.txt
    #   .git/ (should be ignored)
    #   node_modules/ (should be ignored)
    #   file3.txt

    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    (dir1 / "file2.txt").touch()

    sub1 = dir1 / "sub1"
    sub1.mkdir()
    (sub1 / "file1.txt").touch()

    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").touch()

    (tmp_path / "node_modules").mkdir()

    (tmp_path / "file3.txt").touch()

    provider = DirectoryTreeProvider(tmp_path)

    # Stub root() to return tmp_path
    if True:
        res = await provider.resolve(".")

    assert "### Directory Tree: ." in res
    assert "```text" in res
    # The label should be the name of tmp_path since target is "."
    assert tmp_path.name in res
    assert "├── dir1" in res
    assert "│   ├── sub1" in res
    assert "│   │   └── file1.txt" in res
    assert "│   └── file2.txt" in res
    assert "└── file3.txt" in res

    # Assert exclusions
    assert ".git" not in res
    assert "node_modules" not in res


@pytest.mark.asyncio
async def test_tree_provider_resolve_specific_subdir(tmp_path: Path) -> None:
    """Test resolving a specific subdirectory."""
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    (dir1 / "file1.txt").touch()

    provider = DirectoryTreeProvider(tmp_path)

    if True:
        res = await provider.resolve("dir1")

    assert "### Directory Tree: dir1" in res
    assert "dir1\n└── file1.txt" in res


@pytest.mark.asyncio
async def test_tree_provider_not_found(tmp_path: Path) -> None:
    """Test resolution when the directory does not exist."""
    provider = DirectoryTreeProvider(tmp_path)
    if True:
        res = await provider.resolve("non_existent")
    assert "ERROR: Directory 'non_existent' does not exist" in res


@pytest.mark.asyncio
async def test_tree_provider_not_a_dir(tmp_path: Path) -> None:
    """Test resolution when the target is a file."""
    file_path = tmp_path / "file.txt"
    file_path.touch()

    provider = DirectoryTreeProvider(tmp_path)
    if True:
        res = await provider.resolve("file.txt")
    assert "ERROR: Target 'file.txt' is not a directory" in res


@pytest.mark.asyncio
async def test_tree_provider_permission_denied(tmp_path: Path) -> None:
    """Test handling of permission errors."""
    provider = DirectoryTreeProvider(tmp_path)

    with (
        patch.object(Path, "iterdir", side_effect=PermissionError("Denied")),
    ):
        res = await provider.resolve(".")
        assert "[Permission Denied]" in res


@pytest.mark.asyncio
async def test_tree_provider_recursive_error(tmp_path: Path) -> None:
    """Test handling of unexpected errors during recursion."""
    provider = DirectoryTreeProvider(tmp_path)

    with (
        patch.object(Path, "iterdir", side_effect=ValueError("Boom")),
    ):
        res = await provider.resolve(".")
        assert "[Error: Boom]" in res


@pytest.mark.asyncio
async def test_tree_provider_top_level_error(tmp_path: Path) -> None:
    """Test handling of errors before recursion."""
    provider = DirectoryTreeProvider(tmp_path)

    with (
        patch.object(
            DirectoryTreeProvider, "_generate_tree_lines", side_effect=RuntimeError("Top Fail")
        ),
    ):
        res = await provider.resolve(".")
        assert "ERROR: Failed to build directory tree for '.': Top Fail" in res


@pytest.mark.asyncio
async def test_tree_provider_empty_dir(tmp_path: Path) -> None:
    """Test resolving an empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    provider = DirectoryTreeProvider(tmp_path)
    if True:
        res = await provider.resolve("empty")

    assert "### Directory Tree: empty" in res
    # Just the directory name should be there
    assert "empty\n```" in res
