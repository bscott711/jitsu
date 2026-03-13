"""Unit tests for the Jitsu execution models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from jitsu.models.execution import (
    ExecutionResult,
    FileEdit,
    PlannerStage,
    PlannerStatusUpdate,
    ToolRequest,
)


def test_file_edit_initialization() -> None:
    """Test valid instantiation of FileEdit."""
    edit = FileEdit(filepath="src/main.py", content="print('hello')")
    assert edit.filepath == "src/main.py"
    assert edit.content == "print('hello')"


def test_tool_request_initialization() -> None:
    """Test valid instantiation of ToolRequest."""
    req = ToolRequest(tool_name="grep", arguments={"query": "pattern"})
    assert req.tool_name == "grep"
    assert req.arguments == {"query": "pattern"}


def test_execution_result_with_edits() -> None:
    """Test ExecutionResult with a list of file edits."""
    edit = FileEdit(filepath="src/a.py", content="a")
    result = ExecutionResult(thoughts="thought", action=[edit])
    assert result.thoughts == "thought"
    assert isinstance(result.action, list)
    assert result.action[0] == edit


def test_execution_result_with_tool_request() -> None:
    """Test ExecutionResult with a tool request."""
    req = ToolRequest(tool_name="tool", arguments={})
    result = ExecutionResult(thoughts="thought", action=req)
    assert result.thoughts == "thought"
    assert result.action == req


def test_execution_result_invalid_action() -> None:
    """Test ExecutionResult with an invalid action type."""
    with pytest.raises(ValidationError):
        ExecutionResult(thoughts="thought", action="invalid")  # type: ignore


def test_models_frozen() -> None:
    """Test that models are frozen."""
    edit = FileEdit(filepath="a", content="b")
    with pytest.raises(ValidationError, match="Instance is frozen"):
        edit.filepath = "c"

    req = ToolRequest(tool_name="t", arguments={})
    with pytest.raises(ValidationError, match="Instance is frozen"):
        req.tool_name = "u"

    result = ExecutionResult(thoughts="t", action=[])
    with pytest.raises(ValidationError, match="Instance is frozen"):
        result.thoughts = "v"


def test_planner_status_update_valid() -> None:
    """Test valid instantiation of PlannerStatusUpdate."""
    update = PlannerStatusUpdate(
        stage=PlannerStage.INITIALIZING,
        message="Starting...",
        progress_percent=10.0,
    )
    assert update.stage == PlannerStage.INITIALIZING
    assert update.message == "Starting..."
    expected_progress = 10.0
    assert update.progress_percent == expected_progress
    assert isinstance(update.timestamp, datetime)


def test_planner_status_update_invalid_progress() -> None:
    """Test PlannerStatusUpdate with invalid progress ranges."""
    with pytest.raises(ValidationError):
        PlannerStatusUpdate(
            stage=PlannerStage.INITIALIZING,
            message="Too low",
            progress_percent=-1.0,
        )

    with pytest.raises(ValidationError):
        PlannerStatusUpdate(
            stage=PlannerStage.INITIALIZING,
            message="Too high",
            progress_percent=101.0,
        )


def test_planner_status_update_invalid_stage() -> None:
    """Test PlannerStatusUpdate with invalid stage string."""
    with pytest.raises(ValidationError):
        PlannerStatusUpdate(
            stage="invalid-stage",  # type: ignore
            message="Bad stage",
            progress_percent=50.0,
        )
