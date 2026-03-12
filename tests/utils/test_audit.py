"""Tests for the jitsu.utils.audit module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from jitsu.utils.audit import (
    PROJECT_ROOT,
    _scan_file_for_ignores,
    hunt_for_ignores,
    run_command,
)


def test_run_command_success() -> None:
    """Test run_command with a successful execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="Success output", stderr="", returncode=0)
        result = run_command(["echo", "hello"])
        assert result == "Success output"
        mock_run.assert_called_once_with(
            ["echo", "hello"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )


def test_run_command_with_stderr() -> None:
    """Test run_command with output on stderr."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="Some output", stderr="Warning message", returncode=0
        )
        result = run_command(["cmd"])
        assert "Some output" in result
        assert "Warning message" in result


def test_run_command_no_output() -> None:
    """Test run_command with no output on stdout or stderr."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        result = run_command(["cmd"])
        assert result == "No output (Clean pass!)"


def test_run_command_oserror() -> None:
    """Test run_command when subprocess.run raises OSError."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = OSError("Command not found")
        result = run_command(["nonexistent"])
        assert "ERROR running command nonexistent" in result
        assert "Command not found" in result


def test_scan_file_for_ignores_found(tmp_path: Path) -> None:
    """Test _scan_file_for_ignores when targets are found."""
    test_file = tmp_path / "test.py"
    content = "print('hello')  # noqa\nx = 1  # type: ignore\ny = 2  # pyright: ignore\nz = 3\n"
    test_file.write_text(content, encoding="utf-8")

    # Mocking PROJECT_ROOT to be the tmp_path so relative_to works correctly
    # or just ensuring we can handle relative_to PROJECT_ROOT.
    # The actual code uses PROJECT_ROOT.
    # Let's see if we can just let it work or if we need to mock PROJECT_ROOT.
    # Since PROJECT_ROOT is a constant in the module, it might be hard to monkeypatch
    # if it's already imported. But we can try to patch it in the module.

    with patch("jitsu.utils.audit.PROJECT_ROOT", tmp_path):
        hits = _scan_file_for_ignores(test_file)
        expected_hits_count = 3
        assert len(hits) == expected_hits_count
        assert "test.py:1" in hits[0]
        assert "# noqa" in hits[0]
        assert "test.py:2" in hits[1]
        assert "# type: ignore" in hits[1]
        assert "test.py:3" in hits[2]
        assert "# pyright: ignore" in hits[2]


def test_scan_file_for_ignores_clean(tmp_path: Path) -> None:
    """Test _scan_file_for_ignores with no targets."""
    test_file = tmp_path / "clean.py"
    test_file.write_text("print('clean')\n", encoding="utf-8")

    with patch("jitsu.utils.audit.PROJECT_ROOT", tmp_path):
        hits = _scan_file_for_ignores(test_file)
        assert not hits


def test_scan_file_for_ignores_oserror(tmp_path: Path) -> None:
    """Test _scan_file_for_ignores with OSError (e.g. file unreadable)."""
    test_file = tmp_path / "unreadable.py"
    test_file.write_text("content", encoding="utf-8")

    with patch.object(Path, "open", side_effect=OSError("Permission denied")):
        hits = _scan_file_for_ignores(test_file)
        assert len(hits) == 1
        assert "Error reading unreadable.py" in hits[0]
        assert "Permission denied" in hits[0]


def test_scan_file_for_ignores_unicode_error(tmp_path: Path) -> None:
    """Test _scan_file_for_ignores with UnicodeDecodeError."""
    test_file = tmp_path / "binary.py"
    # Write some non-utf8 bytes
    test_file.write_bytes(b"\xff\xfe\xfd")

    hits = _scan_file_for_ignores(test_file)
    assert len(hits) == 1
    assert "Error reading binary.py" in hits[0]


def test_hunt_for_ignores_found(tmp_path: Path) -> None:
    """Test hunt_for_ignores with matching files."""
    module_dir = tmp_path / "mymodule"
    module_dir.mkdir()
    (module_dir / "a.py").write_text("x = 1 # noqa", encoding="utf-8")
    (module_dir / "b.txt").write_text("y = 2 # noqa", encoding="utf-8")  # Should be ignored

    with patch("jitsu.utils.audit.PROJECT_ROOT", tmp_path):
        result = hunt_for_ignores(module_dir)
        assert "mymodule/a.py:1" in result
        assert "# noqa" in result
        assert "b.txt" not in result


def test_hunt_for_ignores_none(tmp_path: Path) -> None:
    """Test hunt_for_ignores when no hits are found."""
    module_dir = tmp_path / "empty"
    module_dir.mkdir()
    (module_dir / "clean.py").write_text("print('ok')", encoding="utf-8")

    result = hunt_for_ignores(module_dir)
    assert result == "No inline ignores found! 🎉"
