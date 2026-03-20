"""Tests for the Jitsu Planner."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jitsu.core.client import LLMClientFactory
from jitsu.core.planner import JitsuPlanner
from jitsu.models.core import (
    AgentDirective,
    ContextTarget,
    EpicBlueprint,
    PhaseBlueprint,
    TargetResolutionMode,
)
from jitsu.models.execution import (
    PlannerOptions,
    PlannerStage,
    PlannerStatusUpdate,
)
from jitsu.prompts import PLANNER_MACRO_PROMPT, TOOLCHAIN_CONSTRAINTS, VERIFICATION_RULE


def mock_response(model_instance: object) -> MagicMock:
    """Create a mock OpenAI chat completion response from a Pydantic model."""
    mock = MagicMock()
    choice = MagicMock()
    choice.message.content = model_instance.model_dump_json()  # type: ignore
    mock.choices = [choice]
    return mock


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    """Clear LLMClientFactory cache before each test."""
    LLMClientFactory.clear_cache()


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
        module_scope=["test"],
        instructions="test",
        completion_criteria=["done"],
        verification_commands=["just verify"],
    )

    mock_client = MagicMock()
    mock_client.client.chat.completions.create.side_effect = [
        mock_response(blueprint),
        mock_response(directive),
    ]

    on_progress_mock = MagicMock()

    planner = JitsuPlanner(objective="Test", relevant_files=["src/main.py"], client=mock_client)

    with (
        patch("jitsu.core.planner.anyio.Path.exists", return_value=False),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        plan = await planner.generate_plan(options=PlannerOptions(on_progress=on_progress_mock))

    assert len(plan) == 1
    assert plan[0].epic_id == "e1"
    assert planner.directives == [directive]

    # Verify progress calls
    expected_calls = 4
    assert on_progress_mock.call_count == expected_calls
    on_progress_mock.assert_any_call("Analyzing scope...")
    on_progress_mock.assert_any_call("Drafting Blueprint...")
    on_progress_mock.assert_any_call("Elaborating Phase 1 (p1)...")
    on_progress_mock.assert_any_call("Planning complete.")

    # Verify prompts
    macro_call = mock_client.client.chat.completions.create.call_args_list[0][1]
    micro_call = mock_client.client.chat.completions.create.call_args_list[1][1]

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
    mock_client.client.chat.completions.create.side_effect = Exception("API error")

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
    blueprint = EpicBlueprint(
        epic_id="e1", phases=[PhaseBlueprint(phase_id="p1", description="d1")]
    )
    directive = AgentDirective(
        epic_id="e1", phase_id="p1", module_scope=["src"], instructions="test"
    )
    mock_client = MagicMock()
    mock_client.client.chat.completions.create.side_effect = [
        mock_response(blueprint),
        mock_response(directive),
    ]

    planner = JitsuPlanner(objective="Test", relevant_files=[], client=mock_client)

    with (
        patch("jitsu.core.planner.anyio.Path.exists", return_value=False),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        await planner.generate_plan()

    # Verify it called create (macro + 1 micro)
    expected_calls = 2
    assert mock_client.client.chat.completions.create.call_count == expected_calls


@pytest.mark.asyncio
async def test_planner_save_plan(tmp_path: Path) -> None:
    """Test saving the validated directives out to a JSON file."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
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
        module_scope=["test"],
        instructions="test",
    )

    mock_client = MagicMock()
    mock_client.client.chat.completions.create.side_effect = [
        mock_response(blueprint),
        mock_response(directive),
    ]

    planner = JitsuPlanner(objective="Test", relevant_files=[], client=mock_client)

    with (
        patch("jitsu.core.planner.anyio.Path.exists", return_value=False),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        await planner.generate_plan(options=PlannerOptions())

    # Features like verbose/typer were removed from the core planner, so we just verify it runs
    assert planner.directives[0].instructions == directive.instructions


@pytest.mark.asyncio
async def test_planner_generate_plan_with_jitsurules() -> None:
    """Test that the planner correctly incorporates .jitsurules if present."""
    blueprint = EpicBlueprint(
        epic_id="e1", phases=[PhaseBlueprint(phase_id="p1", description="d1")]
    )
    mock_client = MagicMock()
    mock_client.client.chat.completions.create.side_effect = [
        mock_response(blueprint),
        mock_response(
            AgentDirective(epic_id="e1", phase_id="p1", module_scope=["src"], instructions="test")
        ),
    ]

    planner = JitsuPlanner(objective="Test", relevant_files=[], client=mock_client)

    with (
        patch("jitsu.core.planner.anyio.Path.exists", side_effect=[True, False]),
        patch("jitsu.core.planner.anyio.Path.read_text", return_value="RULE: Do things"),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        await planner.generate_plan()

    # Verify the system prompt contains the rules
    call = mock_client.client.chat.completions.create.call_args[1]
    system_msg = call["messages"][0]["content"]
    assert "PROJECT RULES (.jitsurules):" in system_msg
    assert "RULE: Do things" in system_msg


def test_planner_compile_phases_logic() -> None:
    """Test the deterministic compile_phases logic."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])

    initial_targets = [
        ContextTarget(provider_name="file", target_identifier="keep.py"),
        ContextTarget(provider_name="file", target_identifier="remove.py"),
    ]
    directive = AgentDirective(
        epic_id="e1",
        phase_id="p1",
        module_scope=["src"],
        instructions="test",
        context_targets=initial_targets,
    )

    # 1. Include only
    transformed = planner.compile_phases([directive], include_paths=["new.py"])
    targets = transformed[0].context_targets
    expected_len_3 = 3
    assert len(targets) == expected_len_3
    assert any(t.target_identifier == "new.py" for t in targets)
    assert any(t.target_identifier == "keep.py" for t in targets)
    assert any(t.target_identifier == "remove.py" for t in targets)

    # 2. Exclude only
    transformed = planner.compile_phases([directive], exclude_paths=["remove.py"])
    targets = transformed[0].context_targets
    expected_len_1 = 1
    assert len(targets) == expected_len_1
    assert targets[0].target_identifier == "keep.py"

    # 3. Combination
    transformed = planner.compile_phases(
        [directive], include_paths=["new.py"], exclude_paths=["remove.py"]
    )
    targets = transformed[0].context_targets
    expected_len_2 = 2
    assert len(targets) == expected_len_2
    assert {t.target_identifier for t in targets} == {"keep.py", "new.py"}

    # 4. No duplicates on include
    transformed = planner.compile_phases([directive], include_paths=["keep.py"])
    targets = transformed[0].context_targets
    assert len(targets) == expected_len_2  # keep.py was already there

    # 5. Empty lists
    transformed = planner.compile_phases([directive], include_paths=[], exclude_paths=[])
    assert transformed[0].context_targets == initial_targets


@pytest.mark.asyncio
async def test_planner_generate_plan_with_injection() -> None:
    """Test that generate_plan correctly applies context injection."""
    blueprint = EpicBlueprint(
        epic_id="e1",
        phases=[PhaseBlueprint(phase_id="p1", description="test phase")],
    )
    directive = AgentDirective(
        epic_id="e1",
        phase_id="p1",
        module_scope=["test"],
        instructions="test",
        context_targets=[ContextTarget(provider_name="file", target_identifier="old.py")],
    )

    mock_client = MagicMock()
    mock_client.client.chat.completions.create.side_effect = [
        mock_response(blueprint),
        mock_response(directive),
    ]

    planner = JitsuPlanner(objective="Test", relevant_files=[], client=mock_client)

    with (
        patch("jitsu.core.planner.anyio.Path.exists", return_value=False),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        plan = await planner.generate_plan(
            options=PlannerOptions(include_paths=["new.py"], exclude_paths=["old.py"])
        )

    expected_len_1 = 1
    assert len(plan) == expected_len_1
    targets = plan[0].context_targets
    assert len(targets) == expected_len_1
    assert targets[0].target_identifier == "new.py"
    assert targets[0].resolution_mode == TargetResolutionMode.FULL_SOURCE


@pytest.mark.asyncio
async def test_planner_structured_callback() -> None:
    """Test the new structured on_status callback."""
    mock_client = MagicMock()
    blueprint = EpicBlueprint(
        epic_id="e1", phases=[PhaseBlueprint(phase_id="p1", description="d1")]
    )
    mock_client.client.chat.completions.create.side_effect = [
        mock_response(blueprint),
        mock_response(
            AgentDirective(epic_id="e1", phase_id="p1", module_scope=["src"], instructions="test")
        ),
    ]

    status_updates = []

    async def on_status(update: PlannerStatusUpdate) -> None:
        status_updates.append(update)

    planner = JitsuPlanner(objective="Test", relevant_files=[], client=mock_client)

    with (
        patch("jitsu.core.planner.anyio.Path.exists", return_value=False),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        await planner.generate_plan(options=PlannerOptions(on_status=on_status))

    assert len(status_updates) > 0
    assert any(u.stage == PlannerStage.ANALYZING_SCOPE for u in status_updates)
    assert any(u.stage == PlannerStage.COMPLETE for u in status_updates)


@pytest.mark.asyncio
async def test_planner_sync_callbacks() -> None:
    """Test sync versions of callbacks in _emit_status."""
    mock_client = MagicMock()
    blueprint = EpicBlueprint(
        epic_id="e1", phases=[PhaseBlueprint(phase_id="p1", description="d1")]
    )
    mock_client.client.chat.completions.create.side_effect = [
        mock_response(blueprint),
        mock_response(
            AgentDirective(epic_id="e1", phase_id="p1", module_scope=["src"], instructions="test")
        ),
    ]

    msgs = []

    def on_progress(msg: str) -> None:
        msgs.append(msg)

    status_updates = []

    def on_status_sync(update: PlannerStatusUpdate) -> None:
        status_updates.append(update)

    planner = JitsuPlanner(
        objective="Test", relevant_files=[], client=mock_client, on_status=on_status_sync
    )

    with (
        patch("jitsu.core.planner.anyio.Path.exists", return_value=False),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        await planner.generate_plan(options=PlannerOptions(on_progress=on_progress))

    assert len(msgs) > 0
    assert len(status_updates) > 0


@pytest.mark.asyncio
async def test_planner_async_legacy_callback() -> None:
    """Test async legacy on_progress callback."""
    mock_client = MagicMock()
    blueprint = EpicBlueprint(
        epic_id="e1", phases=[PhaseBlueprint(phase_id="p1", description="d1")]
    )
    mock_client.client.chat.completions.create.side_effect = [
        mock_response(blueprint),
        mock_response(
            AgentDirective(epic_id="e1", phase_id="p1", module_scope=["src"], instructions="test")
        ),
    ]

    msgs = []

    async def on_progress(msg: str) -> None:
        msgs.append(msg)

    planner = JitsuPlanner(objective="Test", relevant_files=[], client=mock_client)

    with (
        patch("jitsu.core.planner.anyio.Path.exists", return_value=False),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        await planner.generate_plan(options=PlannerOptions(on_progress=on_progress))

    assert len(msgs) > 0


@pytest.mark.asyncio
async def test_generate_plan_injects_toolchain_constraints() -> None:
    """Verify TOOLCHAIN_CONSTRAINTS is injected into the micro-planning prompt."""
    mock_client = MagicMock()

    # 1. Setup mock
    mock_blueprint = EpicBlueprint(
        epic_id="test-epic", phases=[PhaseBlueprint(phase_id="phase-1", description="test phase")]
    )
    mock_directive = AgentDirective(
        epic_id="test-epic",
        phase_id="phase-1",
        module_scope=["src"],
        instructions="test instructions",
        completion_criteria=["done"],
        verification_commands=["uv run pytest"],
    )

    mock_client.client.chat.completions.create.side_effect = [
        mock_response(mock_blueprint),
        mock_response(mock_directive),
    ]

    # 2. Execute
    planner = JitsuPlanner(
        objective="Test objective",
        relevant_files=["test.py"],
        client=mock_client,
    )

    with (
        patch("jitsu.core.planner.anyio.Path.exists", return_value=False),
        patch("jitsu.core.planner.DirectoryTreeProvider.resolve", return_value="tree"),
    ):
        await planner.generate_plan()

    # 3. Assert client was called twice
    expected_call_count = 2
    assert mock_client.client.chat.completions.create.call_count == expected_call_count

    # 4. Extract kwargs from the second call (index 1)
    # call_args_list is a list of call objects, so we must index it to get the specific call
    call_args_list = mock_client.client.chat.completions.create.call_args_list
    second_call = call_args_list[1]
    call_kwargs = second_call.kwargs
    messages = call_kwargs.get("messages", [])

    # 5. Safely find the system message without ["content"] lookups
    system_message = ""
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "system":
            system_message = msg.get("content", "")
            break

    # 6. Verify the toolchain constraints were successfully injected
    assert TOOLCHAIN_CONSTRAINTS in system_message


@pytest.mark.asyncio
async def test_planner_missing_client_safety() -> None:
    """Test RuntimeError when underlying client is None."""
    mock_client = MagicMock()
    mock_client.client = None
    planner = JitsuPlanner(objective="Test", relevant_files=[], client=mock_client)
    with pytest.raises(RuntimeError, match="Underlying LLM client is not initialized"):
        await planner.generate_plan()


@pytest.mark.asyncio
async def test_planner_parse_json_error() -> None:
    """Test RuntimeError when JSON parsing fails."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])
    with pytest.raises(RuntimeError, match="Failed to parse"):
        planner._parse_llm_json("invalid json", EpicBlueprint)


@pytest.mark.asyncio
async def test_planner_parse_validation_error() -> None:
    """Test RuntimeError when Pydantic validation fails."""
    planner = JitsuPlanner(objective="Test", relevant_files=[])
    # Empty JSON will fail validation for EpicBlueprint (requires epic_id)
    with pytest.raises(RuntimeError, match="Failed to parse"):
        planner._parse_llm_json("{}", EpicBlueprint)
