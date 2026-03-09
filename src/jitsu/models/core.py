"""
Core domain models for the Jitsu Context Orchestrator.

These models define the strict contracts between the external orchestrator,
the context providers, and the IDE agents executing the code.
"""

from enum import Enum
from typing import cast

from pydantic import BaseModel, ConfigDict, Field


class PhaseStatus(str, Enum):
    """The allowed statuses an agent can report back to the orchestrator."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    STUCK = "STUCK"


class ContextTarget(BaseModel):
    """
    Defines a specific piece of context the agent needs to complete a task.

    This tells the JIT Context Compiler what to parse and inject.
    """

    model_config = ConfigDict(strict=True, frozen=True)

    provider_name: str = Field(
        ...,
        description=(
            "The registered name of the Context Provider (e.g., 'pydantic_v2', 'sqlalchemy_orm')."
        ),
    )
    target_identifier: str = Field(
        ...,
        description="The specific class, file path, or object to resolve.",
    )
    is_required: bool = Field(
        default=True,
        description=(
            "If True, failure to resolve this context aborts the phase before agent execution."
        ),
    )


class AgentDirective(BaseModel):
    """
    The mathematical 'Ground Truth' instructions for a specific coding phase.

    This replaces stale Markdown files.
    """

    model_config = ConfigDict(strict=True, frozen=True)

    epic_id: str = Field(
        ...,
        description="The parent epic identifier.",
    )
    phase_id: str = Field(
        ...,
        description="The specific phase identifier.",
    )
    module_scope: str = Field(
        ...,
        description="The directory path this agent is allowed to modify (e.g., 'src/auth').",
    )
    instructions: str = Field(
        ...,
        description="The exact functional requirements the agent must execute.",
    )
    context_targets: list[ContextTarget] = Field(
        default_factory=lambda: cast("list[ContextTarget]", []),
        description="Codebase contexts to resolve and inject Just-In-Time.",
    )
    anti_patterns: list[str] = Field(
        default_factory=lambda: cast("list[str]", []),
        description="Strict negative constraints (what NOT to do).",
    )


class PhaseReport(BaseModel):
    """
    The payload the IDE agent sends back to the orchestrator via MCP.

    This is sent when it has finished its work or reached an infinite loop.
    """

    model_config = ConfigDict(strict=True, frozen=True)

    phase_id: str = Field(
        ...,
        description="The ID of the phase being reported on.",
    )
    status: PhaseStatus = Field(
        ...,
        description="The final outcome of the phase execution.",
    )
    artifacts_generated: list[str] = Field(
        default_factory=lambda: cast("list[str]", []),
        description="List of file paths modified or created.",
    )
    agent_notes: str = Field(
        default="",
        description="Any notes or context the agent wants to pass back to the orchestrator.",
    )
