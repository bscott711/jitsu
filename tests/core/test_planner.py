"""Tests for the Jitsu Planner."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jitsu.core.planner import JitsuPlanner
from jitsu.models.core import AgentDirective


@pytest.mark.asyncio
async def test_planner_initialization() -> None:
    """Test the initialization of the planner state."""
    planner = JitsuPlanner(objective="Test", relevant_files=["file1.py"])
    assert planner.objective == "Test"
    assert planner.relevant_files == ["file1.py"]


@pytest.mark.asyncio
async def test_planner_plan_generation_success() -> None:
    """Test that the planner successfully generates a plan using instructor."""
    planner = JitsuPlanner(objective="Test", relevant_files=["src/main.py"])

    directive = AgentDirective(
        epic_id="e1",
        phase_id="p1",
        module_scope="test",
        instructions="test",
        completion_criteria=["done"],
        verification_commands=["just verify"],
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = [directive]

    with (
        patch("jitsu.core.planner.instructor.from_openai", return_value=mock_client),
        patch("jitsu.core.planner.OpenAI"),
        patch("jitsu.core.planner.dotenv.load_dotenv"),
        patch("jitsu.core.planner.os.environ.get", return_value="fake-key"),
        patch("jitsu.core.planner.anyio.Path.exists", return_value=True),
        patch("jitsu.core.planner.anyio.Path.read_text", return_value="system prompt"),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        plan = await planner.generate_plan()

    assert len(plan) == 1
    assert plan[0].epic_id == "e1"
    assert planner._directives == [directive]  # noqa: SLF001


@pytest.mark.asyncio
async def test_planner_missing_api_key() -> None:
    """Test that the planner raises RuntimeError if API key is missing."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])

    with (
        patch("jitsu.core.planner.dotenv.load_dotenv"),
        patch("jitsu.core.planner.os.environ.get", return_value=None),
        pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"),
    ):
        await planner.generate_plan()


@pytest.mark.asyncio
async def test_planner_generation_failure() -> None:
    """Test that the planner allows generation exceptions to bubble up."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API error")

    with (
        patch("jitsu.core.planner.instructor.from_openai", return_value=mock_client),
        patch("jitsu.core.planner.OpenAI"),
        patch("jitsu.core.planner.dotenv.load_dotenv"),
        patch("jitsu.core.planner.os.environ.get", return_value="fake-key"),
        patch("jitsu.core.planner.anyio.Path.exists", return_value=True),
        patch("jitsu.core.planner.anyio.Path.read_text", return_value="system prompt"),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
        pytest.raises(Exception, match="API error"),
    ):
        await planner.generate_plan()


@pytest.mark.asyncio
async def test_planner_generation_fallback_prompt() -> None:
    """Test that the planner uses the fallback prompt if the prompt file is missing."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = []

    with (
        patch("jitsu.core.planner.instructor.from_openai", return_value=mock_client),
        patch("jitsu.core.planner.OpenAI"),
        patch("jitsu.core.planner.dotenv.load_dotenv"),
        patch("jitsu.core.planner.os.environ.get", return_value="fake-key"),
        patch("jitsu.core.planner.anyio.Path.exists", return_value=False),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        await planner.generate_plan()

    # Verify it called create
    mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_planner_save_plan(tmp_path: Path) -> None:
    """Test saving the validated directives out to a JSON file."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        completion_criteria=["done"],
        verification_commands=["just verify"],
    )
    planner._directives = [directive]  # noqa: SLF001

    plan_path = tmp_path / "subdir" / "epic.json"
    planner.save_plan(plan_path)

    assert plan_path.exists()
    data = json.loads(plan_path.read_text())

    assert len(data) == 1
    assert data[0]["epic_id"] == "epic-1"
