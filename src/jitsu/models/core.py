"""Core domain models for the Jitsu orchestration layer."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class PhaseStatus(StrEnum):
    """The execution status of a specific Jitsu phase."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    STUCK = "STUCK"


class TargetResolutionMode(StrEnum):
    """The mode used to resolve JIT context for a target."""

    AUTO = "AUTO"
    STRUCTURE_ONLY = "STRUCTURE_ONLY"
    FULL_SOURCE = "FULL_SOURCE"
    SCHEMA_ONLY = "SCHEMA_ONLY"


class ContextTarget(BaseModel):
    """A specific target for JIT context resolution."""

    model_config = ConfigDict(frozen=True)

    provider_name: str
    target_identifier: str
    is_required: bool = True
    resolution_mode: TargetResolutionMode = TargetResolutionMode.AUTO


class AgentDirective(BaseModel):
    """A task directive sent to an AI agent via MCP."""

    model_config = ConfigDict(frozen=True)

    epic_id: str
    phase_id: str
    module_scope: str
    instructions: str
    context_targets: list[ContextTarget] = []
    anti_patterns: list[str] = []
    verification_commands: list[str] = []
    completion_criteria: list[str] = []


class PhaseReport(BaseModel):
    """A report submitted by an agent upon phase completion."""

    # Allow passing strings that match Enum names/values
    model_config = ConfigDict(use_enum_values=True, frozen=True)

    phase_id: str
    status: PhaseStatus
    artifacts_generated: list[str] = []
    agent_notes: str = ""
    verification_output: str = ""
