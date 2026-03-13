"""Tests for the traceback parser utility."""

from pathlib import Path

from jitsu.utils.traceback_parser import extract_filepaths, filter_local_paths


def test_extract_filepaths_standard_traceback() -> None:
    """Test extracting paths from a standard Python traceback."""
    text = """
    Traceback (most recent call last):
      File "src/jitsu/core/executor.py", line 123, in execute_directive
        success = await self.run_verification(directive.verification_commands)
      File "src/jitsu/core/runner.py", line 45, in run
        return subprocess.run(cmd, shell=True, capture_output=True, text=True)
    """
    paths = extract_filepaths(text)
    assert "src/jitsu/core/executor.py" in paths
    assert "src/jitsu/core/runner.py" in paths


def test_extract_filepaths_pytest_failure() -> None:
    """Test extracting paths from a pytest failure block."""
    text = """
    ___________________ test_execute_directive_failure ____________________
    tests/core/test_executor.py:302: AssertionError
    """
    paths = extract_filepaths(text)
    assert "tests/core/test_executor.py" in paths


def test_extract_filepaths_ruff_failure() -> None:
    """Test extracting paths from a ruff error message."""
    text = """
    src/jitsu/core/executor.py:92:9: F841 local variable 'res' is assigned to but never used
    """
    paths = extract_filepaths(text)
    assert "src/jitsu/core/executor.py" in paths


def test_extract_filepaths_mixed() -> None:
    """Test extracting paths from a mixed error message."""
    text = """
    Check src/jitsu/utils/logger.py for details.
    Error in /absolute/path/to/project/src/jitsu/main.py:10
    Also found "src/jitsu/__init__.py".
    """
    paths = extract_filepaths(text)
    assert "src/jitsu/utils/logger.py" in paths
    assert "/absolute/path/to/project/src/jitsu/main.py" in paths
    assert "src/jitsu/__init__.py" in paths


def test_filter_local_paths(tmp_path: Path) -> None:
    """Test filtering paths to keep only those within the workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    file1 = workspace / "src" / "file1.py"
    file1.parent.mkdir(parents=True)
    file1.write_text("content")

    file2 = workspace / "tests" / "test_file2.py"
    file2.parent.mkdir(parents=True)
    file2.write_text("content")

    # Outside file that exists on disk outside workspace
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "outside.py"
    outside_file.write_text("content")

    # Absolute path within workspace
    abs_path1 = str(file1.resolve())
    # Relative path within workspace
    rel_path2 = "tests/test_file2.py"
    # Path outside workspace
    outside_path = str(outside_file.resolve())
    # Non-existent path
    non_existent = "src/missing.py"

    paths = [abs_path1, rel_path2, outside_path, non_existent]
    filtered = filter_local_paths(paths, workspace)

    assert "src/file1.py" in filtered
    assert "tests/test_file2.py" in filtered
    expected_count = 2
    assert len(filtered) == expected_count
