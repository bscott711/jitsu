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
    """Test that ContextTarget enforces strict typing and immutability."""
    target = ContextTarget(provider_name="test", target_identifier="target")

    # Test frozen (immutability)
    with pytest.raises(ValidationError):
        target.provider_name = "new_provider"  # type: ignore

    # Test strict types (cannot pass string for boolean without failing)
    with pytest.raises(ValidationError):
        ContextTarget(
            provider_name="test",
            target_identifier="target",
            is_required="true",  # type: ignore
        )


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
