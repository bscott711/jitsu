"""State management for the Jitsu MCP Server."""

from typing import Any

from pydantic import TypeAdapter

from jitsu.core.storage import EpicStorage
from jitsu.models.core import AgentDirective, PhaseReport, PhaseStatus


class JitsuStateManager:
    """Manages the in-memory state of agent directives and phase reports."""

    def __init__(self, storage: EpicStorage | None = None) -> None:
        """Initialize an empty state manager."""
        self._queue: list[AgentDirective] = []
        self._reports: list[PhaseReport] = []
        self._phase_to_epic: dict[str, str] = {}
        self._storage = storage or EpicStorage()

    def queue_directive(self, directive: AgentDirective) -> None:
        """
        Add a new directive to the execution queue.

        Args:
            directive: The validated AgentDirective to queue.

        """
        self._queue.append(directive)
        self._phase_to_epic[directive.phase_id] = directive.epic_id

    def get_next_directive(self) -> AgentDirective | None:
        """
        Retrieve and remove the next directive from the queue.

        Returns:
            The next AgentDirective if available, else None.

        """
        if not self._queue:
            return None
        return self._queue.pop(0)

    def update_phase(self, report: PhaseReport) -> str | None:
        """
        Record the outcome of a completed phase (alias for update_phase_status).

        Args:
            report: The phase report submitted by the agent.

        Returns:
            The epic ID associated with the phase, if known.

        """
        return self.update_phase_status(report)

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
        self.clear_queue()

    def get_remaining_count(self, epic_id: str) -> int:
        """
        Return the number of remaining phases in the queue for a specific epic.

        Args:
            epic_id: The ID of the epic to filter by.

        Returns:
            int: The count of pending phases for that epic.

        """
        return sum(1 for d in self._queue if d.epic_id == epic_id)

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

    def hydrate_for_resume(self, epic_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """
        Load the epic state for resumption.

        Args:
            epic_id: The ID of the epic to resume.

        Returns:
            A tuple of (stuck_phase_dict, remaining_phases_list).

        Raises:
            ValueError: If no epic or STUCK phase is found.
            OSError: If files cannot be read.

        """
        path = self._storage.get_current_path(epic_id)
        if not path.exists():
            msg = f"Epic '{epic_id}' not found in current epics."
            raise ValueError(msg)

        content = self._storage.read_text(path)
        adapter = TypeAdapter(list[AgentDirective])
        directives = adapter.validate_json(content)

        state_path = path.with_suffix(".state")
        if not state_path.exists():
            msg = f"No state file found for epic '{epic_id}'. Cannot resume."
            raise ValueError(msg)

        report_content = self._storage.read_text(state_path)
        report = PhaseReport.model_validate_json(report_content)

        if report.status != PhaseStatus.STUCK:
            msg = f"Epic '{epic_id}' is not in STUCK state (status={report.status})."
            raise ValueError(msg)

        # Find the directive in the list
        stuck_idx = -1
        for i, d in enumerate(directives):
            if d.phase_id == report.phase_id:
                stuck_idx = i
                break

        if stuck_idx == -1:
            msg = f"Stuck phase '{report.phase_id}' not found in epic directives."
            raise ValueError(msg)

        current_phase = directives[stuck_idx].model_dump()
        remaining_phases = [d.model_dump() for d in directives[stuck_idx + 1 :]]

        return current_phase, remaining_phases
