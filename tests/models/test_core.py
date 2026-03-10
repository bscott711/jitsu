"""Unit tests for the Jitsu core domain models."""

import pytest
from pydantic import ValidationError

from jitsu.models.core import (
    AgentDirective,
    ContextTarget,
    PhaseReport,
    PhaseStatus,
    TargetResolutionMode,
)


def test_phase_status_enum() -> None:
    """Test the PhaseStatus enum values."""
    assert PhaseStatus.PENDING.value == "PENDING"
    assert PhaseStatus.RUNNING.value == "RUNNING"
    assert PhaseStatus.SUCCESS.value == "SUCCESS"
    assert PhaseStatus.FAILED.value == "FAILED"
    assert PhaseStatus.STUCK.value == "STUCK"


def test_target_resolution_mode_enum() -> None:
    """Test the TargetResolutionMode enum values."""
    assert TargetResolutionMode.AUTO.value == "AUTO"
    assert TargetResolutionMode.STRUCTURE_ONLY.value == "STRUCTURE_ONLY"
    assert TargetResolutionMode.FULL_SOURCE.value == "FULL_SOURCE"
    assert TargetResolutionMode.SCHEMA_ONLY.value == "SCHEMA_ONLY"


def test_context_target_initialization() -> None:
    """Test valid instantiation and defaults of ContextTarget."""
    target = ContextTarget(
        provider_name="pydantic_v2",
        target_identifier="src.schemas.User",
    )
    assert target.provider_name == "pydantic_v2"
    assert target.target_identifier == "src.schemas.User"
    assert target.is_required is True  # Default value
    assert target.resolution_mode == TargetResolutionMode.AUTO  # Default value


def test_context_target_strictness_and_frozen() -> None:
    """Test that ContextTarget is frozen and prevents mutation."""
    target = ContextTarget(provider_name="file_state", target_identifier="src/main.py")

    # Verify the model is frozen and rejects reassignment
    with pytest.raises(ValidationError, match="Instance is frozen"):
        target.provider_name = "new_provider"

    # Verify the model correctly accepts and coerces valid strings to StrEnum
    target_from_dict = ContextTarget.model_validate(
        {
            "provider_name": "file_state",
            "target_identifier": "src/main.py",
            "resolution_mode": "FULL_SOURCE",
        }
    )

    assert target_from_dict.resolution_mode == TargetResolutionMode.FULL_SOURCE


def test_agent_directive_defaults() -> None:
    """Test valid instantiation and default factories of AgentDirective."""
    directive = AgentDirective(
        epic_id="epic-001",
        phase_id="phase-001",
        module_scope="src/auth",
        instructions="Build the auth module.",
    )
    assert directive.epic_id == "epic-001"
    # The default_factory lambdas should be triggered here
    assert directive.context_targets == []
    assert directive.anti_patterns == []


def test_phase_report_defaults() -> None:
    """Test valid instantiation and default factories of PhaseReport."""
    report = PhaseReport(
        phase_id="phase-001",
        status=PhaseStatus.SUCCESS,
    )
    assert report.status == PhaseStatus.SUCCESS
    # The default_factory lambdas should be triggered here
    assert report.artifacts_generated == []
    assert report.agent_notes == ""
    assert report.verification_output == ""


def test_agent_directive_new_fields() -> None:
    """Test the new verification_commands and completion_criteria fields."""
    directive = AgentDirective(
        epic_id="epic-001",
        phase_id="phase-001",
        module_scope="src/auth",
        instructions="Build the auth module.",
        verification_commands=["uv run pytest"],
        completion_criteria=["All tests pass"],
    )
    assert directive.verification_commands == ["uv run pytest"]
    assert directive.completion_criteria == ["All tests pass"]


def test_phase_report_new_fields() -> None:
    """Test the new verification_output field."""
    report = PhaseReport(
        phase_id="phase-001",
        status=PhaseStatus.SUCCESS,
        verification_output="Test passed successfully",
    )
    assert report.verification_output == "Test passed successfully"


def test_agent_directive_strictness_and_frozen() -> None:
    """Test that AgentDirective enforces strict typing and immutability."""
    directive = AgentDirective(
        epic_id="epic-001",
        phase_id="phase-001",
        module_scope="src/auth",
        instructions="Build the auth module.",
    )
    # Test frozen
    with pytest.raises(ValidationError):
        directive.epic_id = "epic-002"  # type: ignore


def test_phase_report_strictness_and_frozen() -> None:
    """Test that PhaseReport enforces strict typing and immutability."""
    report = PhaseReport(
        phase_id="phase-001",
        status=PhaseStatus.SUCCESS,
    )
    # Test frozen
    with pytest.raises(ValidationError):
        report.status = PhaseStatus.FAILED  # type: ignore
