"""State management for the Jitsu MCP Server."""

from pathlib import Path

from jitsu.models.core import AgentDirective, PhaseReport


class JitsuStateManager:
    """Manages the in-memory state of agent directives and phase reports."""

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialize an empty state manager."""
        self.base_dir = base_dir or (Path.cwd() / ".jitsu")
        self.queue_dir = self.base_dir / "queue"
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self._queue: list[AgentDirective] = []
        self._reports: list[PhaseReport] = []
        self._phase_to_epic: dict[str, str] = {}
        # NEW: Track remaining counts per epic for O(1) lookup
        self._epic_remaining: dict[str, int] = {}

    def queue_directive(self, directive: AgentDirective) -> None:
        """
        Add a new directive to the execution queue.

        Args:
            directive: The validated AgentDirective to queue.

        """
        self._queue.append(directive)
        self._phase_to_epic[directive.phase_id] = directive.epic_id
        # NEW: Increment counter for this epic
        epic_id = directive.epic_id
        self._epic_remaining[epic_id] = self._epic_remaining.get(epic_id, 0) + 1

    def get_next_directive(self) -> AgentDirective | None:
        """
        Retrieve and remove the next directive from the queue.

        Returns:
            The next AgentDirective if available, else None.

        """
        if not self._queue:
            return None
        directive = self._queue.pop(0)
        # NEW: Decrement counter for this epic
        epic_id = directive.epic_id
        if epic_id in self._epic_remaining:
            self._epic_remaining[epic_id] -= 1
            if self._epic_remaining[epic_id] <= 0:
                del self._epic_remaining[epic_id]
        return directive

    def update_phase_status(self, report: PhaseReport) -> str | None:
        """
        Record the outcome of a completed phase.

        Args:
            report: The phase report submitted by the agent.

        Returns:
            The epic ID associated with the phase, if known.

        """
        self._reports.append(report)
        return self._phase_to_epic.get(report.phase_id)

    def on_stuck(self, report: PhaseReport) -> None:
        """
        Handle a stuck phase by recording its status and halting the entire queue.

        Args:
            report: The phase report with status PhaseStatus.STUCK.

        """
        self.update_phase_status(report)
        # NEW: Clear epic counters when queue is cleared
        self._epic_remaining.clear()
        self.clear_queue()

    def get_remaining_count(self, epic_id: str) -> int:
        """
        Return the number of remaining phases in the queue for a specific epic.

        Args:
            epic_id: The ID of the epic to filter by.

        Returns:
            int: The count of pending phases for that epic. O(1) lookup.

        """
        return self._epic_remaining.get(epic_id, 0)

    def get_pending_phases(self) -> list[dict[str, str]]:
        """
        Return a list of all pending phases in the queue.

        Returns:
            list[dict[str, str]]: A list of dicts with phase_id and epic_id.

        """
        return [{"phase_id": d.phase_id, "epic_id": d.epic_id} for d in self._queue]

    def clear_queue(self) -> None:
        """Clear all pending directives from the queue."""
        self._queue.clear()
        self._phase_to_epic.clear()
        # NEW: Clear counters too
        self._epic_remaining.clear()

    @property
    def pending_count(self) -> int:
        """
        Return the number of pending directives.

        Returns:
            int: The size of the current queue.

        """
        return len(self._queue)

    @property
    def completed_reports(self) -> list[PhaseReport]:
        """
        Return a copy of all recorded phase reports.

        Returns:
            list[PhaseReport]: A list of all submitted reports.

        """
        return list(self._reports)
