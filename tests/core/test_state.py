"""Unit tests for the Jitsu Core State Manager."""

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
