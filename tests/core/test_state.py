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
        module_scope="src/test",
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

    report = PhaseReport(
        phase_id="phase-001",
        status=PhaseStatus.SUCCESS,
        agent_notes="All tests pass.",
    )

    manager.update_phase_status(report)

    reports = manager.completed_reports
    assert len(reports) == 1
    assert reports[0] == report
