"""Execution models for the Jitsu autonomous agent."""

from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class PlannerStage(str, Enum):
    """Logical stages of the planning process."""

    INITIALIZING = "initializing"
    ANALYZING_SCOPE = "analyzing_scope"
    DRAFTING_PHASES = "drafting_phases"
    VALIDATING_SCHEMA = "validating_schema"
    COMPLETE = "complete"


class PlannerStatusUpdate(BaseModel):
    """A structured status update from the JitsuPlanner."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(default_factory=datetime.now)
    stage: PlannerStage
    message: str
    progress_percent: float = Field(ge=0, le=100)


@runtime_checkable
class PlannerStatusCallback(Protocol):
    """Protocol for planner status update callbacks."""

    async def __call__(self, update: PlannerStatusUpdate) -> None:
        """Handle a status update."""
        ...


class PlannerOptions(BaseModel):
    """Configuration options for a planning session."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str | None = None
    verbose: bool = False
    include_paths: list[str] | None = None
    exclude_paths: list[str] | None = None
    on_progress: Callable[[str], Any] | None = Field(default=None, exclude=True)
    on_status: PlannerStatusCallback | None = Field(default=None, exclude=True)
