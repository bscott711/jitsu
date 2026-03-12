"""Tests for the Jitsu Planner."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jitsu.core.planner import JitsuPlanner
from jitsu.models.core import AgentDirective, EpicBlueprint, PhaseBlueprint
from jitsu.prompts import PLANNER_MACRO_PROMPT, VERIFICATION_RULE


@pytest.mark.asyncio
async def test_planner_initialization() -> None:
    """Test the initialization of the planner state."""
    planner = JitsuPlanner(objective="Test", relevant_files=["file1.py"])
    assert planner.objective == "Test"
    assert planner.relevant_files == ["file1.py"]


@pytest.mark.asyncio
async def test_planner_plan_generation_success() -> None:
    """Test that the planner successfully generates a plan using two passes."""
    blueprint = EpicBlueprint(
        epic_id="e1",
        phases=[PhaseBlueprint(phase_id="p1", description="test phase")],
    )

    directive = AgentDirective(
        epic_id="e1",
        phase_id="p1",
        module_scope="test",
        instructions="test",
        completion_criteria=["done"],
        verification_commands=["just verify"],
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [blueprint, directive]

    on_progress_mock = MagicMock()

    planner = JitsuPlanner(objective="Test", relevant_files=["src/main.py"], client=mock_client)

    with (
        patch("jitsu.core.planner.anyio.Path.exists", return_value=False),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        plan = await planner.generate_plan(on_progress=on_progress_mock)

    assert len(plan) == 1
    assert plan[0].epic_id == "e1"
    assert planner.directives == [directive]

    # Verify progress calls
    expected_calls = 2
    assert on_progress_mock.call_count == expected_calls
    on_progress_mock.assert_any_call("Drafting Epic Blueprint...")
    on_progress_mock.assert_any_call("Elaborating Phase 1 of 1...")

    # Verify prompts
    macro_call = mock_client.chat.completions.create.call_args_list[0][1]
    micro_call = mock_client.chat.completions.create.call_args_list[1][1]

    macro_system = macro_call["messages"][0]["content"]
    assert PLANNER_MACRO_PROMPT in macro_system

    micro_system = micro_call["messages"][0]["content"]
    assert "elaborating a specific Phase" in micro_system
    assert VERIFICATION_RULE in micro_system


@pytest.mark.asyncio
async def test_planner_missing_api_key() -> None:
    """Test that the planner raises RuntimeError if API key is missing."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])

    with (
        patch("jitsu.core.client.dotenv.load_dotenv"),
        patch("jitsu.core.client.os.environ.get", return_value=None),
        pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"),
    ):
        await planner.generate_plan()


@pytest.mark.asyncio
async def test_planner_generation_failure() -> None:
    """Test that the planner allows generation exceptions to bubble up."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API error")

    planner = JitsuPlanner(objective="Test", relevant_files=[], client=mock_client)

    with (
        patch("jitsu.core.planner.anyio.Path.exists", return_value=False),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
        pytest.raises(Exception, match="API error"),
    ):
        await planner.generate_plan()


@pytest.mark.asyncio
async def test_planner_generation_fallback_prompt() -> None:
    """Test that the planner uses the fallback prompt if the prompt file is missing."""
    blueprint = EpicBlueprint(epic_id="e1", phases=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = blueprint

    planner = JitsuPlanner(objective="Test", relevant_files=[], client=mock_client)

    with (
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
    planner.directives = [directive]

    plan_path = tmp_path / "subdir" / "epic.json"
    planner.save_plan(plan_path)

    assert plan_path.exists()
    data = json.loads(plan_path.read_text())

    assert len(data) == 1
    assert data[0]["epic_id"] == "epic-1"


@pytest.mark.asyncio
async def test_planner_generate_plan_verbose() -> None:
    """Test that the planner outputs debug info when verbose is True."""
    blueprint = EpicBlueprint(
        epic_id="e1",
        phases=[PhaseBlueprint(phase_id="p1", description="test phase")],
    )

    directive = AgentDirective(
        epic_id="e1",
        phase_id="p1",
        module_scope="test",
        instructions="test",
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [blueprint, directive]

    planner = JitsuPlanner(objective="Test", relevant_files=[], client=mock_client)

    with (
        patch("jitsu.core.planner.anyio.Path.exists", return_value=False),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
        patch("jitsu.core.planner.typer.secho") as mock_secho,
    ):
        await planner.generate_plan(verbose=True)

    # Verify debug info was printed
    assert mock_secho.called
    # Check for specific strings
    calls = [str(call.args[0]) for call in mock_secho.call_args_list]
    assert any("[DEBUG] Epic Blueprint:" in s for s in calls)
    assert any("[DEBUG] Phase 1 Directive (p1):" in s for s in calls)


@pytest.mark.asyncio
async def test_planner_generate_plan_with_jitsurules() -> None:
    """Test that the planner correctly incorporates .jitsurules if present."""
    blueprint = EpicBlueprint(epic_id="e1", phases=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = blueprint

    planner = JitsuPlanner(objective="Test", relevant_files=[], client=mock_client)

    with (
        patch("jitsu.core.planner.anyio.Path.exists", side_effect=[True, False]),
        patch("jitsu.core.planner.anyio.Path.read_text", return_value="RULE: Do things"),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        await planner.generate_plan()

    # Verify the system prompt contains the rules
    call = mock_client.chat.completions.create.call_args[1]
    system_msg = call["messages"][0]["content"]
    assert "PROJECT RULES (.jitsurules):" in system_msg
    assert "RULE: Do things" in system_msg
