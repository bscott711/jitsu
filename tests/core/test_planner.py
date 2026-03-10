"""Tests for the Jitsu Planner."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

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
async def test_planner_prompt_building() -> None:
    """Test that the planner correctly constructs the LLM prompt."""
    planner = JitsuPlanner(objective="Build a house", relevant_files=["blueprint.pdf"])
    prompt = planner._build_prompt()  # noqa: SLF001

    assert "Build a house" in prompt
    assert "blueprint.pdf" in prompt


@pytest.mark.asyncio
async def test_planner_plan_validation() -> None:
    """Test that the planner successfully validates correct LLM JSON output."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])

    # Mocking litellm.acompletion
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(
            message=AsyncMock(
                content='[{"epic_id": "e1", "phase_id": "p1", "module_scope": "test", "instructions": "test"}]'
            )
        )
    ]

    with pytest.MonkeyPatch.context() as m:
        m.setattr("litellm.acompletion", AsyncMock(return_value=mock_response))
        plan = await planner.generate_plan()

    assert len(plan) == 1
    assert plan[0].epic_id == "e1"


@pytest.mark.asyncio
async def test_planner_empty_llm_response() -> None:
    """Test planner resilience against an empty LLM response string."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content=""))]

    with pytest.MonkeyPatch.context() as m:
        m.setattr("litellm.acompletion", AsyncMock(return_value=mock_response))
        plan = await planner.generate_plan()

    assert len(plan) == 0


@pytest.mark.asyncio
async def test_planner_invalid_llm_response() -> None:
    """Test planner resilience against malformed JSON from the LLM."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="invalid json"))]

    with pytest.MonkeyPatch.context() as m:
        m.setattr("litellm.acompletion", AsyncMock(return_value=mock_response))
        plan = await planner.generate_plan()

    assert len(plan) == 0


@pytest.mark.asyncio
async def test_planner_with_custom_client() -> None:
    """Test that the planner routes to a custom provided client correctly."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = AsyncMock(
        choices=[
            AsyncMock(
                message=AsyncMock(
                    content='[{"epic_id": "e1", "phase_id": "p1", "module_scope": "test", "instructions": "test"}]'
                )
            )
        ]
    )

    planner = JitsuPlanner(objective="Test", relevant_files=[], client=mock_client)
    plan = await planner.generate_plan()

    assert len(plan) == 1
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
    )
    planner._directives = [directive]  # noqa: SLF001

    plan_path = tmp_path / "epic.json"
    planner.save_plan(plan_path)

    assert plan_path.exists()
    # Read the text asynchronously safely using pathlib
    data = json.loads(plan_path.read_text())

    assert len(data) == 1
    assert data[0]["epic_id"] == "epic-1"


@pytest.mark.asyncio
async def test_planner_markdown_json_stripping() -> None:
    """Test that the planner strips markdown json blocks from the LLM response."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])
    mock_response = AsyncMock()

    # Using chr(96)*3 to represent ``` to bypass Canvas markdown parsing bugs
    mock_content = (
        f"{chr(96) * 3}json\n"
        '[{"epic_id": "e1", "phase_id": "p1", "module_scope": "test", "instructions": "test"}]\n'
        f"{chr(96) * 3}"
    )

    mock_response.choices = [AsyncMock(message=AsyncMock(content=mock_content))]

    with pytest.MonkeyPatch.context() as m:
        m.setattr("litellm.acompletion", AsyncMock(return_value=mock_response))
        plan = await planner.generate_plan()

    assert len(plan) == 1
    assert plan[0].epic_id == "e1"


@pytest.mark.asyncio
async def test_planner_markdown_stripping() -> None:
    """Test that the planner strips plain markdown blocks from the LLM response."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])
    mock_response = AsyncMock()

    # Using chr(96)*3 to represent ``` to bypass Canvas markdown parsing bugs
    mock_content = (
        f"{chr(96) * 3}\n"
        '[{"epic_id": "e2", "phase_id": "p1", "module_scope": "test", "instructions": "test"}]\n'
        f"{chr(96) * 3}"
    )

    mock_response.choices = [AsyncMock(message=AsyncMock(content=mock_content))]

    with pytest.MonkeyPatch.context() as m:
        m.setattr("litellm.acompletion", AsyncMock(return_value=mock_response))
        plan = await planner.generate_plan()

    assert len(plan) == 1
    assert plan[0].epic_id == "e2"


@pytest.mark.asyncio
async def test_planner_pydantic_validation_error() -> None:
    """Test planner resilience against valid JSON that fails schema validation."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])
    mock_response = AsyncMock()

    # Valid JSON, but missing required fields like 'module_scope' and 'instructions'
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content='[{"epic_id": "e1", "phase_id": "p1"}]'))
    ]

    with pytest.MonkeyPatch.context() as m:
        m.setattr("litellm.acompletion", AsyncMock(return_value=mock_response))
        plan = await planner.generate_plan()

    # Should safely catch ValidationError and return an empty list
    assert len(plan) == 0
