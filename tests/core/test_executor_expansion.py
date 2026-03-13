"""Tests for dynamic context expansion in JitsuExecutor."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from jitsu.core.executor import JitsuExecutor
from jitsu.models.core import AgentDirective
from jitsu.models.execution import FileEdit, VerificationFailureDetails


@pytest.mark.asyncio
async def test_augment_recovery_message_expands_context(tmp_path: Path) -> None:
    """Test that the recovery message is expanded with out-of-context files from tracebacks."""
    # Setup workspace
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create an "out-of-context" file that is in-scope
    src_dir = workspace / "src"
    src_dir.mkdir()
    dependency_file = src_dir / "dependency.py"
    dependency_file.write_text("def helper(): pass")

    executor = JitsuExecutor(workspace_root=workspace)

    directive = AgentDirective(
        phase_id="test-phase",
        epic_id="test-epic",
        instructions="Fix the bug",
        module_scope=["src"],
        verification_commands=["pytest"],
    )

    # base_message WITHOUT the dependency file
    base_message = "Context:\n<JIT_CONTEXT_MANIFEST>\n- `src/main.py`: **Full Source** (file)\n</JIT_CONTEXT_MANIFEST>"

    # Simulate a traceback that mentions the dependency file
    trimmed_traceback = """
    Traceback (most recent call last):
      File "src/main.py", line 10, in <module>
        from src.dependency import helper
    ImportError: cannot import name 'helper' from 'src.dependency' (src/dependency.py:1)
    """

    details = VerificationFailureDetails(
        summary="Command failed",
        trimmed=trimmed_traceback,
        failed_cmd="pytest",
        failing_file="src/main.py",
    )

    edits = [FileEdit(filepath="src/main.py", content="import helper")]

    # Mock AST provider to return empty for now to focus on expansion
    executor.ast_provider.resolve = AsyncMock(return_value="### AST: src/main.py\n...")

    # Run augmentation
    new_message = await executor.augment_recovery_message(
        base_message=base_message, details=details, edits=edits, directive=directive
    )

    # Assertions
    assert "### File: src/dependency.py" in new_message
    assert "def helper(): pass" in new_message

    # Check that it didn't crash and we have some content
    assert len(new_message) > 0


@pytest.mark.asyncio
async def test_augment_recovery_message_skips_out_of_scope(tmp_path: Path) -> None:
    """Test that out-of-scope files from tracebacks are skipped during expansion."""
    # Setup workspace
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create an "out-of-context" file that is OUT-OF-SCOPE
    other_dir = workspace / "other"
    other_dir.mkdir()
    other_file = other_dir / "external.py"
    other_file.write_text("def external(): pass")

    executor = JitsuExecutor(workspace_root=workspace)

    directive = AgentDirective(
        phase_id="test-phase",
        epic_id="test-epic",
        instructions="Fix the bug",
        module_scope=["src"],  # Only src is in scope
        verification_commands=["pytest"],
    )

    base_message = "Context:\n<JIT_CONTEXT_MANIFEST>\n- `src/main.py`: **Full Source** (file)\n</JIT_CONTEXT_MANIFEST>"

    trimmed_traceback = """
    Traceback (most recent call last):
      File "src/main.py", line 10, in <module>
        import other.external
    ModuleNotFoundError: No module named 'other.external' (other/external.py:1)
    """

    details = VerificationFailureDetails(
        summary="Command failed", trimmed=trimmed_traceback, failed_cmd="pytest"
    )

    new_message = await executor.augment_recovery_message(
        base_message=base_message, details=details, edits=[], directive=directive
    )

    # Should NOT include the out-of-scope file
    assert "### File: other/external.py" not in new_message


@pytest.mark.asyncio
async def test_augment_recovery_message_skips_already_in_context(tmp_path: Path) -> None:
    """Test that files already in context are not added again."""
    # Setup workspace
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    src_dir = workspace / "src"
    src_dir.mkdir()
    main_file = src_dir / "main.py"
    main_file.write_text("print('hello')")

    executor = JitsuExecutor(workspace_root=workspace)

    directive = AgentDirective(
        phase_id="test-phase",
        epic_id="test-epic",
        instructions="Fix the bug",
        module_scope=["src"],
        verification_commands=["pytest"],
    )

    # base_message ALREADY contains src/main.py
    base_message = "Context:\n<JIT_CONTEXT_MANIFEST>\n- `src/main.py`: **Full Source** (file)\n</JIT_CONTEXT_MANIFEST>"

    trimmed_traceback = """
    File "src/main.py", line 1, in <module>
    """

    details = VerificationFailureDetails(
        summary="Command failed", trimmed=trimmed_traceback, failed_cmd="pytest"
    )

    new_message = await executor.augment_recovery_message(
        base_message=base_message, details=details, edits=[], directive=directive
    )

    # Should NOT include src/main.py AGAIN (especially not as full source if it was already there)
    # The count of "File: src/main.py" should be 0 if it was in manifest but not in details as full source yet
    # Or rather, it shouldn't be added by the dynamic expansion logic.
    expected_count = 0
    assert new_message.count("### File: src/main.py") == expected_count
