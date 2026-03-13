"""Unit tests for the Jitsu core domain models."""

import pytest
from pydantic import ValidationError

from jitsu.models.core import (
    AgentDirective,
    ContextInjectionConfig,
    ContextTarget,
    EpicBlueprint,
    PhaseReport,
    PhaseStatus,
    ResumeResult,
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


def test_context_injection_config() -> None:
    """Test the ContextInjectionConfig model."""
    config = ContextInjectionConfig(include=["file1.py"], exclude=["file2.py"])
    assert config.include == ["file1.py"]
    assert config.exclude == ["file2.py"]

    # Test defaults
    default_config = ContextInjectionConfig()
    assert default_config.include == []
    assert default_config.exclude == []

    # Test frozen
    with pytest.raises(ValidationError):
        config.include = ["new.py"]


def test_context_target_initialization() -> None:
    """Test valid instantiation and defaults of ContextTarget."""
    target = ContextTarget(
        provider_name="pydantic",
        target_identifier="src.schemas.User",
    )
    assert target.provider_name == "pydantic"
    assert target.target_identifier == "src.schemas.User"
    assert target.is_required is True  # Default value
    assert target.resolution_mode == TargetResolutionMode.AUTO  # Default value


def test_context_target_strictness_and_frozen() -> None:
    """Test that ContextTarget is frozen and prevents mutation."""
    target = ContextTarget(provider_name="file", target_identifier="src/main.py")

    # Verify the model is frozen and rejects reassignment
    with pytest.raises(ValidationError, match="Instance is frozen"):
        target.provider_name = "new_provider"

    # Verify the model correctly accepts and coerces valid strings to StrEnum
    target_from_dict = ContextTarget.model_validate(
        {
            "provider_name": "file",
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
        module_scope=["src/auth"],
        instructions="Build the auth module.",
    )
    assert directive.epic_id == "epic-001"
    # The default_factory lambdas should be triggered here
    assert directive.context_targets == []
    assert directive.anti_patterns == []
    assert directive.context_injection is None


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
        module_scope=["src/auth"],
        instructions="Build the auth module.",
        verification_commands=["uv run pytest"],
        completion_criteria=["All tests pass"],
    )
    assert directive.verification_commands == ["uv run pytest", "just verify"]
    assert directive.completion_criteria == ["All tests pass"]


def test_agent_directive_with_injection_config() -> None:
    """Test AgentDirective with context_injection field."""
    config = ContextInjectionConfig(include=["inc.py"])
    directive = AgentDirective(
        epic_id="epic-001",
        phase_id="phase-001",
        module_scope=["src"],
        instructions="test",
        context_injection=config,
    )
    assert directive.context_injection == config
    assert directive.context_injection.include == ["inc.py"]


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
        module_scope=["src/auth"],
        instructions="Build the auth module.",
    )
    # Test frozen
    with pytest.raises(ValidationError):
        directive.epic_id = "epic-002"


def test_phase_report_strictness_and_frozen() -> None:
    """Test that PhaseReport enforces strict typing and immutability."""
    report = PhaseReport(
        phase_id="phase-001",
        status=PhaseStatus.SUCCESS,
    )
    # Test frozen
    with pytest.raises(ValidationError):
        report.status = PhaseStatus.FAILED


def test_resume_result_model() -> None:
    """Test the ResumeResult model."""
    result = ResumeResult(
        phase_id="phase-001",
        status=PhaseStatus.SUCCESS,
        reason="Manual fix applied",
    )
    assert result.phase_id == "phase-001"
    assert result.status == PhaseStatus.SUCCESS
    assert result.reason == "Manual fix applied"

    # Test defaults
    result_default = ResumeResult(
        phase_id="phase-002",
        status=PhaseStatus.STUCK,
    )
    assert result_default.reason is None

    # Test frozen
    with pytest.raises(ValidationError):
        result.phase_id = "phase-003"


def test_context_target_invalid_provider() -> None:
    """Test that ContextTarget rejects invalid provider names."""
    with pytest.raises(ValidationError, match="Invalid provider name 'invalid'"):
        ContextTarget(provider_name="invalid", target_identifier="src/main.py")


def test_epic_blueprint_empty_phases() -> None:
    """Test that EpicBlueprint rejects an empty phases list."""
    with pytest.raises(ValidationError, match="Epic must have at least one phase"):
        EpicBlueprint(epic_id="epic-001", phases=[])


def test_agent_directive_invalid_module_scope() -> None:
    """Test that AgentDirective rejects empty or invalid module_scope."""
    # Test empty list
    with pytest.raises(
        ValidationError, match="module_scope must contain at least one non-empty string"
    ):
        AgentDirective(
            epic_id="epic-001",
            phase_id="phase-001",
            module_scope=[],
            instructions="test",
        )

    # Test list with only empty strings
    with pytest.raises(
        ValidationError, match="module_scope must contain at least one non-empty string"
    ):
        AgentDirective(
            epic_id="epic-001",
            phase_id="phase-001",
            module_scope=["", "  "],
            instructions="test",
        )


def test_agent_directive_verification_bypass_prevention() -> None:
    """Test that 'just verify' is automatically added to verification_commands."""
    directive = AgentDirective(
        epic_id="epic-001",
        phase_id="phase-001",
        module_scope=["src"],
        instructions="test",
        verification_commands=["ls -R"],
    )
    assert "just verify" in directive.verification_commands

    # Test when it's already there
    directive2 = AgentDirective(
        epic_id="epic-001",
        phase_id="phase-001",
        module_scope=["src"],
        instructions="test",
        verification_commands=["just verify", "other command"],
    )
    assert directive2.verification_commands.count("just verify") == 1
