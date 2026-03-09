"""Tests for the project root resolution utility."""

from pathlib import Path
from unittest.mock import patch

import pytest

import jitsu.utils.path as path_module
from jitsu.utils.path import get_project_root, root


def test_get_project_root_success(tmp_path: Path) -> None:
    """Test successful resolution of the project root."""
    (tmp_path / "pyproject.toml").touch()
    fake_file = tmp_path / "src" / "jitsu" / "utils" / "path.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.touch()

    with patch("jitsu.utils.path.__file__", str(fake_file)):
        assert get_project_root() == tmp_path


def test_get_project_root_failure(tmp_path: Path) -> None:
    """Test resolution failure when pyproject.toml is missing."""
    fake_file = tmp_path / "src" / "path.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.touch()

    with (
        patch("jitsu.utils.path.__file__", str(fake_file)),
        pytest.raises(RuntimeError, match=r"Could not find pyproject.toml"),
    ):
        get_project_root()


def test_root_caching() -> None:
    """Test that the project root is cached after the first lookup."""
    # Built-in way to clear the lru_cache for pure test isolation
    path_module.root.cache_clear()

    with patch("jitsu.utils.path.get_project_root") as mock_get:
        mock_get.return_value = Path("/fake/root")

        res1 = root()
        res2 = root()

        assert res1 == Path("/fake/root")
        assert res1 is res2
        mock_get.assert_called_once()
