"""Unit tests for the Jitsu Core State Manager."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from jitsu.core.state import JitsuStateManager
from jitsu.models.core import AgentDirective, PhaseReport, PhaseStatus


def test_state_manager_initialization() -> None:
    """Test that the state manager initializes completely empty."""
    manager = JitsuStateManager()
    assert manager.pending_count == 0
    assert len(manager.completed_reports) == 0
    assert manager.get_next_directive() is None


def test_state_manager_queue_and_get() -> None:
    """Test queuing and popping directives (FIFO)."""
    manager = JitsuStateManager()

    directive = AgentDirective(
        epic_id="epic-001",
        phase_id="phase-001",
        module_scope=["src/test"],
        instructions="Test instructions.",
    )

    manager.queue_directive(directive)
    assert manager.pending_count == 1

    # Retrieve the directive and ensure it was removed from the queue
    popped = manager.get_next_directive()
    assert popped == directive
    assert manager.pending_count == 0
    assert manager.get_next_directive() is None


def test_state_manager_update_status() -> None:
    """Test recording phase reports."""
    manager = JitsuStateManager()

    directive = AgentDirective(
        epic_id="epic-001",
        phase_id="phase-001",
        module_scope=["src/test"],
        instructions="Test",
    )
    manager.queue_directive(directive)

    report = PhaseReport(
        phase_id="phase-001",
        status=PhaseStatus.SUCCESS,
        agent_notes="All tests pass.",
    )

    epic_id = manager.update_phase_status(report)
    assert epic_id == "epic-001"

    reports = manager.completed_reports
    assert len(reports) == 1
    assert reports[0] == report


def test_state_manager_remaining_count() -> None:
    """Test correctly calculating remaining phases for an epic."""
    manager = JitsuStateManager()
    d1 = AgentDirective(epic_id="epic-1", phase_id="p1", module_scope=["s"], instructions="i")
    d2 = AgentDirective(epic_id="epic-1", phase_id="p2", module_scope=["s"], instructions="i")
    d3 = AgentDirective(epic_id="epic-2", phase_id="p3", module_scope=["s"], instructions="i")

    manager.queue_directive(d1)
    manager.queue_directive(d2)
    manager.queue_directive(d3)

    expected_remaining = 2
    assert manager.get_remaining_count("epic-1") == expected_remaining
    assert manager.get_remaining_count("epic-2") == 1

    manager.get_next_directive()  # remove p1
    assert manager.get_remaining_count("epic-1") == 1


def test_state_manager_pending_phases() -> None:
    """Test retrieving list of pending phases."""
    manager = JitsuStateManager()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["src/test"],
        instructions="Test",
    )
    manager.queue_directive(directive)

    pending = manager.get_pending_phases()
    assert len(pending) == 1
    assert pending[0]["phase_id"] == "phase-1"
    assert pending[0]["epic_id"] == "epic-1"


def test_state_manager_on_stuck() -> None:
    """Test that on_stuck records the report and clears the queue."""
    manager = JitsuStateManager()
    d1 = AgentDirective(epic_id="epic-1", phase_id="p1", module_scope=["s"], instructions="i")
    d2 = AgentDirective(epic_id="epic-1", phase_id="p2", module_scope=["s"], instructions="i")
    manager.queue_directive(d1)
    manager.queue_directive(d2)

    report = PhaseReport(phase_id="p1", status=PhaseStatus.STUCK, agent_notes="Stuck")
    manager.on_stuck(report)

    assert manager.pending_count == 0
    assert len(manager.completed_reports) == 1
    assert manager.completed_reports[0].status == PhaseStatus.STUCK


def test_hydrate_for_resume_success(tmp_path: Path) -> None:
    """Test successful hydration for resumption."""
    storage = MagicMock()
    epic_id = "test-resume"
    epic_path = tmp_path / f"{epic_id}.json"
    state_path = tmp_path / f"{epic_id}.state"

    storage.get_current_path.return_value = epic_path

    d1 = AgentDirective(epic_id=epic_id, phase_id="p1", module_scope=["s"], instructions="i1")
    d2 = AgentDirective(epic_id=epic_id, phase_id="p2", module_scope=["s"], instructions="i2")

    epic_path.write_text(json.dumps([d1.model_dump(), d2.model_dump()]))
    storage.read_text.side_effect = lambda p: p.read_text()

    report = PhaseReport(phase_id="p1", status=PhaseStatus.STUCK, agent_notes="stuck")
    state_path.write_text(report.model_dump_json())

    manager = JitsuStateManager(storage=storage)
    current, remaining = manager.hydrate_for_resume(epic_id)

    assert current["phase_id"] == "p1"
    assert len(remaining) == 1
    assert remaining[0]["phase_id"] == "p2"


def test_hydrate_for_resume_not_stuck(tmp_path: Path) -> None:
    """Test hydration fails if the phase is not STUCK."""
    storage = MagicMock()
    epic_id = "test-not-stuck"
    epic_path = tmp_path / f"{epic_id}.json"
    state_path = tmp_path / f"{epic_id}.state"
    storage.get_current_path.return_value = epic_path

    epic_path.write_text("[]")
    report = PhaseReport(phase_id="p1", status=PhaseStatus.SUCCESS)
    state_path.write_text(report.model_dump_json())
    storage.read_text.side_effect = lambda p: p.read_text()

    manager = JitsuStateManager(storage=storage)
    with pytest.raises(ValueError, match="is not in STUCK state"):
        manager.hydrate_for_resume(epic_id)


def test_hydrate_for_resume_missing_phase(tmp_path: Path) -> None:
    """Test hydration fails if the STUCK phase is missing from directives."""
    storage = MagicMock()
    epic_id = "test-missing-phase"
    epic_path = tmp_path / f"{epic_id}.json"
    state_path = tmp_path / f"{epic_id}.state"
    storage.get_current_path.return_value = epic_path

    epic_path.write_text("[]")
    report = PhaseReport(phase_id="p1", status=PhaseStatus.STUCK)
    state_path.write_text(report.model_dump_json())
    storage.read_text.side_effect = lambda p: p.read_text()

    manager = JitsuStateManager(storage=storage)
    with pytest.raises(ValueError, match="not found in epic directives"):
        manager.hydrate_for_resume(epic_id)


def test_hydrate_for_resume_no_epic(tmp_path: Path) -> None:
    """Test hydration fails if the epic file is missing."""
    storage = MagicMock()
    storage.get_current_path.return_value = tmp_path / "missing.json"
    manager = JitsuStateManager(storage=storage)
    with pytest.raises(ValueError, match="not found in current epics"):
        manager.hydrate_for_resume("missing")


def test_hydrate_for_resume_no_state(tmp_path: Path) -> None:
    """Test hydration fails if the state file is missing."""
    storage = MagicMock()
    epic_id = "test-no-state"
    epic_path = tmp_path / f"{epic_id}.json"
    epic_path.write_text("[]")
    storage.get_current_path.return_value = epic_path
    storage.read_text.side_effect = lambda p: p.read_text()
    manager = JitsuStateManager(storage=storage)
    with pytest.raises(ValueError, match="No state file found"):
        manager.hydrate_for_resume(epic_id)
