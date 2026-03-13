"""Unit tests for the Jitsu execution models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from jitsu.models.execution import (
    PlannerStage,
    PlannerStatusUpdate,
)


def test_planner_status_update_valid() -> None:
    """Test valid instantiation of PlannerStatusUpdate."""
    update = PlannerStatusUpdate(
        stage=PlannerStage.INITIALIZING,
        message="Starting...",
        progress_percent=10.0,
    )
    assert update.stage == PlannerStage.INITIALIZING
    assert update.message == "Starting..."
    expected_progress = 10.0
    assert update.progress_percent == expected_progress
    assert isinstance(update.timestamp, datetime)


def test_planner_status_update_invalid_progress() -> None:
    """Test PlannerStatusUpdate with invalid progress ranges."""
    with pytest.raises(ValidationError):
        PlannerStatusUpdate(
            stage=PlannerStage.INITIALIZING,
            message="Too low",
            progress_percent=-1.0,
        )

    with pytest.raises(ValidationError):
        PlannerStatusUpdate(
            stage=PlannerStage.INITIALIZING,
            message="Too high",
            progress_percent=101.0,
        )


def test_planner_status_update_invalid_stage() -> None:
    """Test PlannerStatusUpdate with invalid stage string."""
    with pytest.raises(ValidationError):
        PlannerStatusUpdate(
            stage="invalid-stage",  # type: ignore
            message="Bad stage",
            progress_percent=50.0,
        )
