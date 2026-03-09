"""Core domain models for the Jitsu orchestration layer."""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class PhaseStatus(str, Enum):
    """The execution status of a specific Jitsu phase."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    STUCK = "STUCK"


class ContextTarget(BaseModel):
    """A specific target for JIT context resolution."""

    model_config = ConfigDict(frozen=True, strict=True)

    provider_name: str
    target_identifier: str
    is_required: bool = True


class AgentDirective(BaseModel):
    """A task directive sent to an AI agent via MCP."""

    epic_id: str
    phase_id: str
    module_scope: str
    instructions: str
    context_targets: list[ContextTarget] = []
    anti_patterns: list[str] = []


class PhaseReport(BaseModel):
    """A report submitted by an agent upon phase completion."""

    # Allow passing strings that match Enum names/values
    model_config = ConfigDict(use_enum_values=True)

    phase_id: str
    status: PhaseStatus
    artifacts_generated: list[str] = []
    agent_notes: str = ""
