"""Core domain models for the Jitsu orchestration layer."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ALLOWED_PROVIDERS = {
    "file",
    "pydantic",
    "ast",
    "tree",
    "directory_tree",
    "git",
    "env_var",
    "markdown_ast",
}


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


class ContextInjectionConfig(BaseModel):
    """Configuration for deterministic context injection and exclusion."""

    model_config = ConfigDict(frozen=True)

    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class PhaseBlueprint(BaseModel):
    """A high-level blueprint for a single Jitsu phase."""

    model_config = ConfigDict(frozen=True)

    phase_id: str
    description: str


class EpicBlueprint(BaseModel):
    """A high-level blueprint for a multi-phase Jitsu epic."""

    model_config = ConfigDict(frozen=True)

    epic_id: str
    phases: list[PhaseBlueprint]

    @model_validator(mode="after")
    def validate_phases_not_empty(self) -> "EpicBlueprint":
        """Ensure that the epic has at least one phase."""
        if not self.phases:
            msg = "Epic must have at least one phase."
            raise ValueError(msg)
        return self


class ContextTarget(BaseModel):
    """A specific target for JIT context resolution."""

    model_config = ConfigDict(frozen=True)

    provider_name: str = Field(
        ...,
        description="The exact name of the provider (e.g., 'file', 'ast', 'pydantic', etc.).",
    )
    target_identifier: str = Field(
        ...,
        description="The path or identifier for the target (e.g., 'src/main.py').",
    )
    is_required: bool = True
    resolution_mode: TargetResolutionMode = TargetResolutionMode.AUTO

    @field_validator("provider_name")
    @classmethod
    def validate_provider_name(cls, v: str) -> str:
        """Ensure the provider name is supported."""
        if v not in ALLOWED_PROVIDERS:
            msg = f"Invalid provider name '{v}'. Allowed providers are: {', '.join(sorted(ALLOWED_PROVIDERS))}"
            raise ValueError(msg)
        return v


class AgentDirective(BaseModel):
    """A task directive sent to an AI agent via MCP."""

    model_config = ConfigDict(frozen=True)

    epic_id: str
    phase_id: str
    module_scope: list[str]
    instructions: str
    context_targets: list[ContextTarget] = Field(default=[])
    anti_patterns: list[str] = Field(default=[])
    verification_commands: list[str] = Field(
        default=[],
        description="Commands to verify the phase is complete.",
    )
    completion_criteria: list[str] = Field(default=[])
    context_injection: ContextInjectionConfig | None = None

    @model_validator(mode="after")
    def validate_module_scope_not_empty(self) -> "AgentDirective":
        """Ensure that the module scope is not empty and contains valid paths."""
        if not self.module_scope or not any(s.strip() for s in self.module_scope):
            msg = "module_scope must contain at least one non-empty string."
            raise ValueError(msg)
        return self

    @field_validator("verification_commands")
    @classmethod
    def enforce_zero_bypass_verification(cls, v: list[str]) -> list[str]:
        """Mechanically guarantee that the verification pipeline cannot be bypassed."""
        if not any("just verify" in cmd for cmd in v):
            v.append("just verify")
        return v


class PhaseReport(BaseModel):
    """A report submitted by an agent upon phase completion."""

    # Allow passing strings that match Enum names/values
    model_config = ConfigDict(use_enum_values=True, frozen=True)

    phase_id: str
    status: PhaseStatus
    artifacts_generated: list[str] = Field(default=[])
    agent_notes: str = ""
    verification_output: str = ""
