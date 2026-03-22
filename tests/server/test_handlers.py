"""Tests for the ToolHandlers class."""

import json
import subprocess
import typing
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

from jitsu.core.compiler import ContextCompiler
from jitsu.core.state import JitsuStateManager
from jitsu.models.core import AgentDirective
from jitsu.server.handlers import ToolHandlers

EXPECTED_TOOL_COUNT = 13


@pytest.fixture
def state_manager() -> JitsuStateManager:
    """Provide a fresh StateManager."""
    return JitsuStateManager()


@pytest.fixture
def context_compiler() -> ContextCompiler:
    """Provide a fresh ContextCompiler."""
    return ContextCompiler()


@pytest.fixture
def handlers(state_manager: JitsuStateManager, context_compiler: ContextCompiler) -> ToolHandlers:
    """Provide ToolHandlers with its dependencies."""
    return ToolHandlers(state_manager=state_manager, context_compiler=context_compiler)


@pytest.mark.asyncio
async def test_handle_get_next_phase_empty(handlers: ToolHandlers) -> None:
    """Test getting a phase when the queue is empty."""
    result = await handlers.handle_get_next_phase()
    assert isinstance(result[0], TextContent)
    assert result[0].text == "No pending phases in the queue."


@pytest.mark.asyncio
async def test_handle_get_next_phase_with_data(
    handlers: ToolHandlers, state_manager: JitsuStateManager
) -> None:
    """Test getting a phase when data exists in the queue."""
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["src/test"],
        instructions="Do a thing",
    )
    state_manager.queue_directive(directive)

    result = await handlers.handle_get_next_phase()
    assert isinstance(result[0], TextContent)
    assert "phase-1" in result[0].text


@pytest.mark.asyncio
async def test_handle_report_status_success(
    handlers: ToolHandlers, state_manager: JitsuStateManager
) -> None:
    """Test reporting a successful status."""
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-success",
        module_scope=["src/test"],
        instructions="Test",
    )
    state_manager.queue_directive(directive)
    state_manager.get_next_directive()

    result = handlers.handle_report_status({"phase_id": "phase-success", "status": "SUCCESS"})
    assert isinstance(result[0], TextContent)
    assert "ACK. 0 phases remaining." in result[0].text


@pytest.mark.asyncio
async def test_handle_report_status_other(handlers: ToolHandlers) -> None:
    """Test reporting a non-success status or success with no epic_id."""
    result = handlers.handle_report_status({"phase_id": "phase-1", "status": "FAILED"})
    assert isinstance(result[0], TextContent)
    assert "Successfully recorded status FAILED" in result[0].text


@pytest.mark.asyncio
async def test_handle_report_status_missing_args(handlers: ToolHandlers) -> None:
    """Test reporting status with missing arguments."""
    result = handlers.handle_report_status(None)
    assert isinstance(result[0], TextContent)
    assert "Error: Missing arguments." in result[0].text


@pytest.mark.asyncio
async def test_handle_report_status_invalid(handlers: ToolHandlers) -> None:
    """Test reporting an invalid status."""
    result = handlers.handle_report_status({"phase_id": "phase-1", "status": "INVALID_STATUS"})
    assert isinstance(result[0], TextContent)
    assert "Validation Error" in result[0].text


@pytest.mark.asyncio
async def test_handle_inspect_queue_empty(handlers: ToolHandlers) -> None:
    """Test inspecting an empty queue."""
    result = handlers.handle_inspect_queue()
    assert isinstance(result[0], TextContent)
    assert "The queue is currently empty." in result[0].text


@pytest.mark.asyncio
async def test_handle_inspect_queue(
    handlers: ToolHandlers, state_manager: JitsuStateManager
) -> None:
    """Test inspecting the queue."""
    directive = AgentDirective(
        epic_id="epic-inspect",
        phase_id="phase-inspect",
        module_scope=["src/test"],
        instructions="Test",
    )
    state_manager.queue_directive(directive)

    result = handlers.handle_inspect_queue()
    assert isinstance(result[0], TextContent)
    assert "phase-inspect" in result[0].text


@pytest.mark.asyncio
async def test_handle_request_context_success(handlers: ToolHandlers) -> None:
    """Test successful JIT context request."""
    # We'll use a real file to test the FileStateProvider
    result = await handlers.handle_request_context(
        {"target_identifier": "pyproject.toml", "provider_name": "file"}
    )
    assert isinstance(result[0], TextContent)
    assert "not found" in result[0].text or "[" in result[0].text


@pytest.mark.asyncio
async def test_handle_request_context_missing_args(handlers: ToolHandlers) -> None:
    """Test context request with missing arguments."""
    result = await handlers.handle_request_context({})
    assert isinstance(result[0], TextContent)
    assert "Error: Missing target_identifier" in result[0].text


@pytest.mark.asyncio
async def test_handle_request_context_unknown_provider(handlers: ToolHandlers) -> None:
    """Test context request with an unknown provider."""
    result = await handlers.handle_request_context(
        {"target_identifier": "test", "provider_name": "unknown"}
    )
    assert isinstance(result[0], TextContent)
    assert "Error: Unknown provider 'unknown'" in result[0].text


@pytest.mark.asyncio
async def test_handle_get_planning_context(handlers: ToolHandlers) -> None:
    """Test getting planning context."""
    with patch("jitsu.server.handlers.DirectoryTreeProvider") as mock_tree_cls:
        mock_tree = mock_tree_cls.return_value
        mock_tree.resolve = AsyncMock(return_value="### Tree\n- src")

        with (
            patch("anyio.Path.exists", AsyncMock(return_value=True)),
            patch("anyio.Path.read_text", AsyncMock(return_value="RULE 1")),
        ):
            result = await handlers.handle_get_planning_context({})
            assert isinstance(result[0], TextContent)
            assert "### Tree" in result[0].text
            assert "RULE 1" in result[0].text


@pytest.mark.asyncio
async def test_handle_get_planning_context_no_rules(handlers: ToolHandlers) -> None:
    """Test getting planning context without .jitsurules."""
    with patch("jitsu.server.handlers.DirectoryTreeProvider") as mock_tree_cls:
        mock_tree = mock_tree_cls.return_value
        mock_tree.resolve = AsyncMock(return_value="### Tree")
        with patch("anyio.Path.exists", AsyncMock(return_value=False)):
            result = await handlers.handle_get_planning_context({})
            assert "(Not found)" in result[0].text


@pytest.mark.asyncio
async def test_handle_submit_epic_success(
    handlers: ToolHandlers, state_manager: JitsuStateManager
) -> None:
    """Test successfully submitting an epic."""
    directive_data: dict[str, object] = {
        "epic_id": "epic-new",
        "phase_id": "phase-new",
        "module_scope": ["src"],
        "instructions": "Go",
    }

    result = handlers.handle_submit_epic({"directives": [directive_data]})
    assert "Successfully queued 1 phases." in result[0].text
    assert state_manager.pending_count == 1


@pytest.mark.asyncio
async def test_handle_submit_epic_errors(handlers: ToolHandlers) -> None:
    """Test handle_submit_epic error paths."""
    # Missing args
    result = handlers.handle_submit_epic({})
    assert "Missing 'directives' argument" in result[0].text

    # Not a list
    result = handlers.handle_submit_epic({"directives": "not a list"})
    assert "'directives' must be a list" in result[0].text

    # Validation Error
    result = handlers.handle_submit_epic({"directives": [{"bad": "data"}]})
    assert "Validation Error" in result[0].text

    # Internal Error
    with patch(
        "jitsu.server.handlers.AgentDirective.model_validate", side_effect=RuntimeError("BOOM")
    ):
        result = handlers.handle_submit_epic({"directives": [{"good": "data"}]})
        assert "Internal Error: BOOM" in result[0].text


@pytest.mark.asyncio
async def test_handle_git_status(handlers: ToolHandlers) -> None:
    """Test the git_status handler."""
    mock_status = "M src/main.py"
    with patch("jitsu.server.handlers.GitProvider") as mock_cls:
        mock_instance = mock_cls.return_value
        mock_instance.resolve = AsyncMock(
            return_value=f"### Git Status\n```text\n{mock_status}\n```"
        )

        result = await handlers.handle_git_status()
        assert isinstance(result[0], TextContent)
        assert mock_status in result[0].text


@pytest.mark.asyncio
async def test_handle_git_commit_success(handlers: ToolHandlers) -> None:
    """Test successful git_commit."""
    with patch("jitsu.server.handlers.CommandRunner.run_args") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = handlers.handle_git_commit({"message": "feat: add git tools", "sync": True})
        assert isinstance(result[0], TextContent)
        assert "Successfully committed and pushed" in result[0].text


@pytest.mark.asyncio
async def test_handle_git_commit_errors(handlers: ToolHandlers) -> None:
    """Test git_commit error paths."""
    # Missing message
    result = handlers.handle_git_commit({})
    assert "Missing 'message' argument" in result[0].text

    # CalledProcessError
    error = subprocess.CalledProcessError(returncode=1, cmd="just commit")
    error.stderr = "git error"
    with patch("jitsu.server.handlers.CommandRunner.run_args", side_effect=error):
        result = handlers.handle_git_commit({"message": "feat: test"})
        assert "Error: Git command failed" in result[0].text
        assert "git error" in result[0].text


@pytest.mark.asyncio
async def test_handle_git_commit_invalid_message(handlers: ToolHandlers) -> None:
    """Test git_commit with invalid conventional commit message."""
    result = handlers.handle_git_commit({"message": "bad message"})
    assert isinstance(result[0], TextContent)
    assert "MUST follow Conventional Commits" in result[0].text


@pytest.mark.asyncio
async def test_register_all(handlers: ToolHandlers) -> None:
    """Test that register_all calls registry.register the correct number of times."""
    mock_registry = MagicMock()
    handlers.register_all(mock_registry)
    assert mock_registry.register.call_count == EXPECTED_TOOL_COUNT


@pytest.mark.asyncio
async def test_handle_report_status_stuck(
    handlers: ToolHandlers, state_manager: JitsuStateManager
) -> None:
    """Test reporting a STUCK status halts the epic."""
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-stuck",
        module_scope=["src"],
        instructions="Test",
    )
    state_manager.queue_directive(directive)
    state_manager.queue_directive(
        AgentDirective(epic_id="epic-1", phase_id="p2", module_scope=["s"], instructions="i")
    )
    expected_pending = 2
    assert state_manager.pending_count == expected_pending

    # The tool returns a list of TextContent
    result = handlers.handle_report_status({"phase_id": "phase-stuck", "status": "STUCK"})
    assert isinstance(result[0], TextContent)
    assert "Epic HALTED" in result[0].text
    assert state_manager.pending_count == 0


@pytest.mark.asyncio
async def test_handle_plan_epic_success(handlers: ToolHandlers) -> None:
    """Test successfully planning an epic."""
    mock_directive = AgentDirective(
        epic_id="epic-planned",
        phase_id="phase-1",
        module_scope=["src"],
        instructions="Plan",
    )

    with (
        patch("jitsu.server.handlers.JitsuPlanner") as mock_planner_cls,
        patch("jitsu.server.handlers.EpicStorage") as mock_storage_cls,
    ):
        mock_planner = mock_planner_cls.return_value
        mock_planner.generate_plan = AsyncMock(return_value=[mock_directive])
        mock_planner.directives = [mock_directive]
        mock_planner.epic_id = "epic-planned"

        mock_storage = mock_storage_cls.return_value
        mock_storage.get_current_path.return_value = Path("epic-planned.json")
        mock_storage.rel_path.return_value = ".jitsu/epics/epic-planned.json"

        result = await handlers.handle_plan_epic({"prompt": "New epic"})

        assert "Successfully generated epic 'epic-planned'" in result[0].text
        assert ".jitsu/epics/epic-planned.json" in result[0].text
        mock_planner.generate_plan.assert_called_once()
        mock_planner.save_plan.assert_called_once()


@pytest.mark.asyncio
async def test_handle_plan_epic_missing_prompt(handlers: ToolHandlers) -> None:
    """Test planning an epic without a prompt."""
    result = await handlers.handle_plan_epic({})
    assert "Error: Missing 'prompt' argument." in result[0].text


@pytest.mark.asyncio
async def test_handle_plan_epic_failure(handlers: ToolHandlers) -> None:
    """Test planning an epic when generation fails."""
    with patch("jitsu.server.handlers.JitsuPlanner") as mock_planner_cls:
        mock_planner = mock_planner_cls.return_value
        mock_planner.generate_plan = AsyncMock(return_value=[])
        mock_planner.directives = []

        result = await handlers.handle_plan_epic({"prompt": "Fail epic"})
        assert "Error: Failed to generate plan." in result[0].text


@pytest.mark.asyncio
async def test_handle_plan_epic_with_progress(
    state_manager: JitsuStateManager, context_compiler: ContextCompiler
) -> None:
    """Test handle_plan_epic with progress notifications."""
    mock_server = AsyncMock()
    handlers = ToolHandlers(
        state_manager=state_manager, context_compiler=context_compiler, server=mock_server
    )

    mock_directive = AgentDirective(
        epic_id="epic-progress",
        phase_id="p1",
        module_scope=["src"],
        instructions="Plan",
    )

    with (
        patch("jitsu.server.handlers.JitsuPlanner") as mock_planner_cls,
        patch("jitsu.server.handlers.EpicStorage") as mock_storage_cls,
        patch("sys.stderr.write") as mock_stderr,
        patch("sys.stderr.flush"),
    ):
        mock_planner = mock_planner_cls.return_value
        mock_planner.generate_plan = AsyncMock(return_value=[mock_directive])
        mock_planner.directives = [mock_directive]

        mock_storage = mock_storage_cls.return_value
        mock_storage.get_current_path.return_value = Path("epic.json")

        arguments: dict[str, object] = {
            "prompt": "Progress test",
            "_metadata": {"progressToken": "token-123"},
        }
        await handlers.handle_plan_epic(arguments)

        # Retrieve the on_progress callback passed to generate_plan
        _, kwargs = mock_planner.generate_plan.call_args
        on_progress = kwargs["options"].on_progress

        # Call the callback
        await on_progress("Test message")

        # Verify stderr output
        mock_stderr.assert_called_with("[* progress] Test message\n")

        # Verify MCP notification
        mock_server.request_context.session.send_progress_notification.assert_called_once()


@pytest.mark.asyncio
async def test_extract_progress_token_none_args(handlers: ToolHandlers) -> None:
    """Test extracting progress token with None arguments."""
    assert handlers._extract_progress_token(None) is None


@pytest.mark.asyncio
async def test_extract_progress_token_invalid_candidate(handlers: ToolHandlers) -> None:
    """Test extracting progress token with an invalid candidate type."""
    arguments = {"_metadata": {"progressToken": ["not", "a", "string"]}}
    assert handlers._extract_progress_token(typing.cast("dict[str, object]", arguments)) is None


@pytest.mark.asyncio
async def test_execute_plan_workflow_no_epic_id(handlers: ToolHandlers) -> None:
    """Test executing plan workflow when epic_id is missing."""
    with patch("jitsu.server.handlers.JitsuPlanner") as mock_planner_cls:
        mock_planner = mock_planner_cls.return_value
        mock_planner.generate_plan = AsyncMock()
        mock_planner.directives = [MagicMock()]
        mock_planner.epic_id = None  # Missing epic_id

        result = await handlers._execute_plan_workflow("test", [], AsyncMock())
        assert result is None


@pytest.mark.asyncio
async def test_handle_check_coverage_success(handlers: ToolHandlers) -> None:
    """Test successful coverage check with JSON output."""
    mock_result = MagicMock()
    mock_result.returncode = 0

    mock_json: dict[str, typing.Any] = {
        "files": {"test_module.py": {"missing_lines": [1, 2, 3, 5]}}
    }

    with (
        patch("anyio.Path.exists", AsyncMock(return_value=True)),
        patch("anyio.Path.read_text", AsyncMock(return_value=json.dumps(mock_json))),
        patch("anyio.Path.unlink", AsyncMock()),
        patch("jitsu.core.runner.CommandRunner.run_args", return_value=mock_result),
    ):
        result = await handlers.handle_check_coverage(
            {"test_file_path": "test_file.py", "module_scope": ["test_module"]}
        )
        assert isinstance(result[0], TextContent)
        expected = {"test_module.py": [1, 2, 3, 5]}
        assert json.loads(result[0].text) == expected


@pytest.mark.asyncio
async def test_handle_check_coverage_no_missing(handlers: ToolHandlers) -> None:
    """Test coverage check with no missing lines."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_json: dict[str, typing.Any] = {"files": {"test_module.py": {"missing_lines": []}}}

    with (
        patch("anyio.Path.exists", AsyncMock(return_value=True)),
        patch("anyio.Path.read_text", AsyncMock(return_value=json.dumps(mock_json))),
        patch("anyio.Path.unlink", AsyncMock()),
        patch("jitsu.core.runner.CommandRunner.run_args", return_value=mock_result),
    ):
        result = await handlers.handle_check_coverage(
            {"test_file_path": "test_file.py", "module_scope": ["test_module"]}
        )
        assert isinstance(result[0], TextContent)
        assert result[0].text == "{}"


@pytest.mark.asyncio
async def test_handle_check_coverage_file_not_found(handlers: ToolHandlers) -> None:
    """Test coverage check when test file is missing."""
    with patch("anyio.Path.exists", AsyncMock(return_value=False)):
        result = await handlers.handle_check_coverage(
            {"test_file_path": "non_existent.py", "module_scope": ["test_module"]}
        )
        assert "Test file not found" in result[0].text


@pytest.mark.asyncio
async def test_handle_check_coverage_empty_scope(handlers: ToolHandlers) -> None:
    """Test coverage check with empty module scope."""
    with patch("anyio.Path.exists", AsyncMock(return_value=True)):
        result = await handlers.handle_check_coverage(
            {"test_file_path": "test_file.py", "module_scope": []}
        )
        assert "module_scope' cannot be empty" in result[0].text


@pytest.mark.asyncio
async def test_handle_check_coverage_missing_args(handlers: ToolHandlers) -> None:
    """Test coverage check with missing arguments."""
    result = await handlers.handle_check_coverage({})
    assert "Missing 'test_file_path' or 'module_scope'" in result[0].text


@pytest.mark.asyncio
async def test_handle_check_coverage_pytest_error(handlers: ToolHandlers) -> None:
    """Test coverage check when pytest fails unexpectedly."""
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = "Internal Pytest Error"
    mock_result.returncode = 2

    with (
        patch("anyio.Path.exists", AsyncMock(return_value=True)),
        patch("anyio.Path.unlink", AsyncMock()),
        patch("jitsu.core.runner.CommandRunner.run_args", return_value=mock_result),
    ):
        result = await handlers.handle_check_coverage(
            {"test_file_path": "test_file.py", "module_scope": ["test_module"]}
        )
        assert "Pytest failed" in result[0].text


@pytest.mark.asyncio
async def test_handle_check_coverage_internal_error(handlers: ToolHandlers) -> None:
    """Test coverage check with an unexpected exception."""
    # This specifically triggers the Exception catch block
    with patch("anyio.Path.exists", AsyncMock(side_effect=RuntimeError("Unexpected"))):
        result = await handlers.handle_check_coverage(
            {"test_file_path": "test_file.py", "module_scope": ["test_module"]}
        )
        assert "Unexpected" in result[0].text


@pytest.mark.asyncio
async def test_handle_check_coverage_json_not_found(handlers: ToolHandlers) -> None:
    """Test coverage check when JSON file is not generated."""
    mock_result = MagicMock()
    mock_result.returncode = 0

    with (
        patch("anyio.Path.exists", AsyncMock(side_effect=[True, False, False])),
        patch("anyio.Path.unlink", AsyncMock()),
        patch("jitsu.core.runner.CommandRunner.run_args", return_value=mock_result),
    ):
        result = await handlers.handle_check_coverage(
            {"test_file_path": "test_file.py", "module_scope": ["test_module"]}
        )
        assert "Coverage JSON file was not generated" in result[0].text


@pytest.mark.asyncio
async def test_handle_plan_epic_verbose(
    state_manager: JitsuStateManager, context_compiler: ContextCompiler
) -> None:
    """Test handle_plan_epic with verbose=True."""
    mock_server = AsyncMock()
    handlers = ToolHandlers(
        state_manager=state_manager, context_compiler=context_compiler, server=mock_server
    )

    mock_directive = AgentDirective(
        epic_id="epic-progress",
        phase_id="p1",
        module_scope=["src"],
        instructions="Plan",
    )

    with (
        patch("jitsu.server.handlers.JitsuPlanner") as mock_planner_cls,
        patch("jitsu.server.handlers.EpicStorage") as mock_storage_cls,
        patch("sys.stderr.write") as mock_stderr,
        patch("sys.stderr.flush"),
    ):
        mock_planner = mock_planner_cls.return_value
        mock_planner.generate_plan = AsyncMock(return_value=[mock_directive])
        mock_planner.directives = [mock_directive]

        mock_storage = mock_storage_cls.return_value
        mock_storage.get_current_path.return_value = Path("epic.json")

        arguments: dict[str, object] = {
            "prompt": "Verbose test",
            "verbose": True,
        }
        await handlers.handle_plan_epic(arguments)

        # Retrieve the on_progress callback passed to generate_plan
        _, kwargs = mock_planner.generate_plan.call_args
        options = kwargs["options"]

        assert options.verbose is True

        # Call the callback
        if options.on_progress:
            await options.on_progress("Verbose test message")

        # Verify stderr output
        mock_stderr.assert_called_with("Verbose test message\n")
