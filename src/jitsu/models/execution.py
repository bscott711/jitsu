"""Execution models for the Jitsu autonomous agent."""

from datetime import datetime
from enum import Enum

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
