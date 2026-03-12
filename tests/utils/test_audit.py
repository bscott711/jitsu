"""Tests for the jitsu.utils.audit module."""

import runpy
from pathlib import Path
from unittest.mock import MagicMock, patch

import jitsu.utils.audit as audit_module
from jitsu.utils.audit import (
    MODULES_TO_AUDIT,
    PROJECT_ROOT,
    _scan_file_for_ignores,
    hunt_for_ignores,
    main,
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
    content = f"print('hello')  # n{'oqa'}\nx = 1  # t{'ype: ignore'}\ny = 2  # py{'right: ignore'}\nz = 3\n"
    test_file.write_text(content, encoding="utf-8")

    with patch("jitsu.utils.audit.PROJECT_ROOT", tmp_path):
        hits = _scan_file_for_ignores(test_file)
        expected_hits_count = 3
        assert len(hits) == expected_hits_count
        assert "test.py:1" in hits[0]
        assert "# n" + "oqa" in hits[0]
        assert "test.py:2" in hits[1]
        assert "# t" + "ype: ignore" in hits[1]
        assert "test.py:3" in hits[2]
        assert f"# py{'right: ignore'}" in hits[2]


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
    (module_dir / "a.py").write_text("x = 1 # n" + "oqa", encoding="utf-8")
    (module_dir / "b.txt").write_text("y = 2 # n" + "oqa", encoding="utf-8")  # Should be ignored

    with patch("jitsu.utils.audit.PROJECT_ROOT", tmp_path):
        result = hunt_for_ignores(module_dir)
        assert "mymodule/a.py:1" in result
        assert "# n" + "oqa" in result
        assert "b.txt" not in result


def test_hunt_for_ignores_none(tmp_path: Path) -> None:
    """Test hunt_for_ignores when no hits are found."""
    module_dir = tmp_path / "empty"
    module_dir.mkdir()
    (module_dir / "clean.py").write_text("print('ok')", encoding="utf-8")

    result = hunt_for_ignores(module_dir)
    assert result == "No inline ignores found! 🎉"


def test_main_success() -> None:
    """Test the main() function for a successful run."""
    with (
        patch("jitsu.utils.audit.OUTPUT_DIR") as mock_output_dir,
        patch("jitsu.utils.audit.datetime") as mock_datetime,
        patch("jitsu.utils.audit.run_command") as mock_run_cmd,
        patch("jitsu.utils.audit.hunt_for_ignores") as mock_hunt,
        patch("jitsu.utils.audit.typer.secho") as mock_secho,
        patch("jitsu.utils.audit.PROJECT_ROOT") as mock_project_root,
    ):
        # Setup mocks
        mock_datetime.now.return_value.strftime.return_value = "2026-03-12 12:00:00 UTC"
        mock_run_cmd.return_value = "Mock command output"
        mock_hunt.return_value = "No inline ignores found! 🎉"

        # Mock project root path structure
        mock_module = MagicMock(spec=Path)
        mock_module.exists.return_value = True
        mock_module.name = "core"
        mock_project_root.__truediv__.return_value = mock_module

        # Mock report file
        mock_report_file = MagicMock(spec=Path)
        mock_output_dir.__truediv__.return_value = mock_report_file
        mock_report_file.relative_to.return_value = Path("docs/report.md")

        main()

        # Check side effects
        mock_output_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        assert mock_secho.called
        assert mock_report_file.write_text.call_count == len(MODULES_TO_AUDIT)

        # Verify content of the first call
        args, _ = mock_report_file.write_text.call_args_list[0]
        content = args[0]
        assert "# V2 Audit Report: `src/jitsu/core`" in content
        assert "2026-03-12 12:00:00 UTC" in content


def test_main_skip_nonexistent(tmp_path: Path) -> None:
    """Test main() skips modules that do not exist."""
    with (
        patch("jitsu.utils.audit.OUTPUT_DIR") as mock_output_dir,
        patch("jitsu.utils.audit.typer.secho") as mock_secho,
        patch("jitsu.utils.audit.PROJECT_ROOT", tmp_path),
    ):
        # tmp_path is empty, so no modules exist
        main()

        # Should have called secho for each skipped module
        # MODULES_TO_AUDIT length is 3
        assert mock_secho.call_count == len(MODULES_TO_AUDIT)
        assert "Skipping" in mock_secho.call_args_list[0][0][0]
        # Should not have created files
        assert not mock_output_dir.__truediv__.called


def test_main_block() -> None:
    """Test the if __name__ == '__main__' block."""
    mock_res = MagicMock()
    mock_res.stdout = "Mock output"
    mock_res.stderr = ""
    with (
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.write_text"),
        patch("subprocess.run", return_value=mock_res),
        patch("typer.secho"),
    ):
        runpy.run_path(audit_module.__file__, run_name="__main__")
