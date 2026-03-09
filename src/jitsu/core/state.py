"""State management for the Jitsu MCP Server."""

from jitsu.models.core import AgentDirective, PhaseReport


class JitsuStateManager:
    """Manages the in-memory state of agent directives and phase reports."""

    def __init__(self) -> None:
        """Initialize an empty state manager."""
        self._queue: list[AgentDirective] = []
        self._reports: list[PhaseReport] = []

    def queue_directive(self, directive: AgentDirective) -> None:
        """
        Add a new directive to the execution queue.

        Args:
            directive: The validated AgentDirective to queue.

        """
        self._queue.append(directive)

    def get_next_directive(self) -> AgentDirective | None:
        """
        Retrieve and remove the next directive from the queue.

        Returns:
            The next AgentDirective if available, else None.

        """
        if not self._queue:
            return None
        return self._queue.pop(0)

    def update_phase_status(self, report: PhaseReport) -> None:
        """
        Record the outcome of a completed phase.

        Args:
            report: The phase report submitted by the agent.

        """
        self._reports.append(report)

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
