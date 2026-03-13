"""Tests for the Jitsu CLI main module."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pytest
import typer
from typer.testing import CliRunner

from jitsu.cli.main import app, main
from jitsu.core.orchestrator import JitsuOrchestrator
from jitsu.core.storage import EpicStorage
from jitsu.models.core import AgentDirective
from jitsu.server.client import send_payload
from jitsu.server.mcp_server import state_manager

runner = CliRunner()


@pytest.fixture(autouse=True)
def clear_state() -> None:
    """Clear the global state manager queue before each test."""
    while state_manager.get_next_directive():
        pass


@patch("jitsu.cli.main.anyio.run")
def test_cli_serve(mock_run: MagicMock) -> None:
    """Test the CLI serve command runs the server."""
    result = runner.invoke(app, ["serve"])

    assert result.exit_code == 0, (
        f"Command failed:\nOUTPUT: {result.output}\nEXC: {result.exception}"
    )
    mock_run.assert_called_once()
    assert "Starting Jitsu MCP Server" in result.output


@patch("jitsu.cli.main.anyio.run", side_effect=KeyboardInterrupt)
def test_cli_serve_keyboard_interrupt(mock_run: MagicMock) -> None:
    """Test the CLI handles KeyboardInterrupt exits cleanly."""
    result = runner.invoke(app, ["serve"])

    assert result.exit_code == 0, (
        f"Command failed:\nOUTPUT: {result.output}\nEXC: {result.exception}"
    )
    mock_run.assert_called_once()
    assert "Shutting down Jitsu MCP Server" in result.output


@patch("jitsu.cli.main.anyio.run", side_effect=RuntimeError("Test mock error"))
def test_cli_serve_exception(mock_run: MagicMock) -> None:
    """Test the CLI handles generic exceptions."""
    result = runner.invoke(app, ["serve"])

    assert result.exit_code == 1, (
        f"Command failed:\nOUTPUT: {result.output}\nEXC: {result.exception}"
    )
    mock_run.assert_called_once()
    assert "Fatal error during server execution: Test mock error" in result.output


@patch("jitsu.cli.main.anyio.run")
def test_cli_serve_with_valid_epic(mock_run: MagicMock, tmp_path: Path) -> None:
    """Test serving with a valid epic JSON file."""
    epic_file = tmp_path / "epic.json"
    valid_data = [
        {
            "epic_id": "test-epic",
            "phase_id": "phase-1",
            "module_scope": ["test"],
            "instructions": "do the thing",
        }
    ]
    epic_file.write_text(json.dumps(valid_data), encoding="utf-8")

    result = runner.invoke(app, ["serve", "--epic", str(epic_file)])

    assert result.exit_code == 0
    mock_run.assert_called_once()
    assert "Successfully queued 1 phase" in result.output

    # Verify the global state manager actually captured it
    directive = state_manager.get_next_directive()
    assert directive is not None
    assert directive.epic_id == "test-epic"


@patch("jitsu.cli.main.anyio.run")
def test_cli_serve_with_invalid_epic(mock_run: MagicMock, tmp_path: Path) -> None:
    """Test serving with an epic JSON file that fails Pydantic validation."""
    epic_file = tmp_path / "epic_invalid.json"
    invalid_data = [{"epic_id": "test-epic"}]  # Missing required fields like phase_id
    epic_file.write_text(json.dumps(invalid_data), encoding="utf-8")

    result = runner.invoke(app, ["serve", "--epic", str(epic_file)])

    assert result.exit_code == 1
    mock_run.assert_not_called()  # Server should not start on failure
    assert "Validation Error parsing" in result.output


@patch("jitsu.cli.main.anyio.run")
def test_cli_serve_with_unreadable_epic(mock_run: MagicMock, tmp_path: Path) -> None:
    """Test serving with an epic JSON file that cannot be read."""
    epic_file = tmp_path / "epic_error.json"
    epic_file.touch()

    # Force a read error using our mock
    with patch.object(EpicStorage, "read_text", side_effect=OSError("Access Denied")):
        result = runner.invoke(app, ["serve", "--epic", str(epic_file)])

    assert result.exit_code == 1
    mock_run.assert_not_called()
    assert "Failed to read" in result.output
    assert "Access Denied" in result.output


def test_cli_main() -> None:
    """Test the direct main() entrypoint executes the Typer app."""
    with patch.object(sys, "argv", ["jitsu", "--help"]), pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0


@patch("jitsu.cli.main.anyio.run")
def test_cli_submit_success(
    mock_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test successful epic submission via CLI."""
    # Change working directory to tmp_path so 'epics/completed' is created there
    monkeypatch.chdir(tmp_path)

    epic_file = tmp_path / "epic.json"
    epic_file.write_text("[]", encoding="utf-8")

    mock_run.return_value = "ACK: Queued 0 phase(s)."

    result = runner.invoke(app, ["submit", "--epic", str(epic_file)])

    assert result.exit_code == 0
    assert "ACK: Queued 0 phase(s)." in result.output
    assert "Epic archived to epics/completed/epic.json" in result.output

    # Verify file was moved
    completed_file = tmp_path / "epics" / "completed" / "epic.json"
    assert completed_file.exists()
    assert not epic_file.exists()

    mock_run.assert_called_once()


@patch("jitsu.cli.main.anyio.run")
def test_cli_submit_server_error(
    mock_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test epic submission handles ERR: responses correctly."""
    monkeypatch.chdir(tmp_path)

    epic_file = tmp_path / "epic.json"
    epic_file.write_text("[]", encoding="utf-8")

    mock_run.return_value = "ERR: Invalid Schema"

    result = runner.invoke(app, ["submit", "--epic", str(epic_file)])

    assert result.exit_code == 1
    assert "ERR: Invalid Schema" in result.output

    # Verify file was NOT moved
    completed_file = tmp_path / "epics" / "completed" / "epic.json"
    assert not completed_file.exists()
    assert epic_file.exists()

    mock_run.assert_called_once()


@patch.object(EpicStorage, "read_bytes", side_effect=OSError("Read error"))
def test_cli_submit_failure(mock_read: MagicMock, tmp_path: Path) -> None:
    """Test epic submission file read failure handling."""
    epic_file = tmp_path / "epic.json"
    epic_file.write_text("[]", encoding="utf-8")

    result = runner.invoke(app, ["submit", "--epic", str(epic_file)])

    assert result.exit_code == 1
    assert "Failed to read epic file: Read error" in result.output
    mock_read.assert_called_once()


@pytest.mark.asyncio
async def test_send_payload_success() -> None:
    """Test internal send_payload helper on success."""
    mock_client = AsyncMock()
    mock_client.receive.return_value = b"ACK: Queued 1 phase(s)."

    with patch("jitsu.server.client.anyio.connect_tcp", (mock_connect := AsyncMock())):
        mock_connect.return_value.__aenter__.return_value = mock_client
        response = await send_payload(b"test", port=1234)

        mock_connect.assert_called_once_with("127.0.0.1", 1234)
        mock_client.send.assert_called_once_with(b"test")
        mock_client.send_eof.assert_called_once()
        assert response == "ACK: Queued 1 phase(s)."


@pytest.mark.asyncio
async def test_send_payload_end_of_stream() -> None:
    """Test internal send_payload helper handles EOF cleanly."""
    mock_client = AsyncMock()
    mock_client.receive.side_effect = anyio.EndOfStream()

    with patch("jitsu.server.client.anyio.connect_tcp", (mock_connect := AsyncMock())):
        mock_connect.return_value.__aenter__.return_value = mock_client
        response = await send_payload(b"test", port=1234)

        assert response == "ERR: Server closed connection without responding."


@pytest.mark.asyncio
async def test_send_payload_connection_refused() -> None:
    """Test send_payload when the server connection is refused."""
    with patch("jitsu.server.client.anyio.connect_tcp", side_effect=ConnectionRefusedError()):
        with pytest.raises(typer.Exit) as exc:
            await send_payload(b"test")
        assert exc.value.exit_code == 1


@patch("jitsu.cli.main.JitsuOrchestrator", autospec=True)
def test_cli_plan_success(mock_orch_cls: MagicMock, tmp_path: Path) -> None:
    """Test successful plan generation via CLI."""
    out_file = tmp_path / "epic.json"
    mock_orch = mock_orch_cls.return_value
    # Mock a directive to avoid index error
    mock_directive = MagicMock(spec=AgentDirective)
    mock_directive.epic_id = "test-epic"
    mock_orch.execute_plan.return_value = [mock_directive]

    # Trigger callback when execute_plan is called
    async def side_effect(*_args: object, **_kwargs: object) -> list[AgentDirective]:
        # Create the file that the code expects to exist after planning
        # In actual call: objective, files, actual_out
        if len(_args) > 2:  # noqa: PLR2004
            out_path = _args[2]
            if isinstance(out_path, Path):
                await anyio.Path(out_path).write_text("[]", encoding="utf-8")

        on_progress = mock_orch_cls.call_args[1].get("on_progress")
        if on_progress:
            on_progress("Task started")
        return [mock_directive]

    mock_orch.execute_plan.side_effect = side_effect

    result = runner.invoke(
        app, ["plan", "Build a cool feature", "--out", str(out_file), "-m", "gpt-4o"]
    )

    assert result.exit_code == 0
    assert "Generating plan for: 'Build a cool feature'" in result.output
    assert "Using model: gpt-4o" in result.output
    assert "Task started" in result.output
    mock_orch.execute_plan.assert_awaited_once()
    assert out_file.exists()


@patch.object(JitsuOrchestrator, "execute_plan", new_callable=AsyncMock)
def test_cli_plan_failure(mock_execute: AsyncMock, tmp_path: Path) -> None:
    """Test plan generation failure via CLI."""
    mock_execute.side_effect = typer.Exit(1)
    out_file = tmp_path / "epic.json"

    result = runner.invoke(app, ["plan", "Build a cool feature", "--out", str(out_file)])

    assert result.exit_code == 1
    mock_execute.assert_awaited_once()


@patch.object(JitsuOrchestrator, "execute_plan", new_callable=AsyncMock)
def test_cli_plan_with_files(mock_execute: AsyncMock, tmp_path: Path) -> None:
    """Test plan generation with provided context files."""
    out_file = tmp_path / "epic.json"
    ctx_file = tmp_path / "context_file.py"
    ctx_file.touch()

    # Mock a directive to avoid index error
    mock_directive = MagicMock(spec=AgentDirective)
    mock_directive.epic_id = "test-epic"
    mock_execute.return_value = [mock_directive]

    async def side_effect(*_args: object, **_kwargs: object) -> list[AgentDirective]:
        if len(_args) > 2:  # noqa: PLR2004
            out_path = _args[2]
            if isinstance(out_path, Path):
                await anyio.Path(out_path).write_text("[]", encoding="utf-8")
        return [mock_directive]

    mock_execute.side_effect = side_effect

    result = runner.invoke(
        app, ["plan", "Feature", "--file", str(ctx_file), "--out", str(out_file)]
    )

    assert result.exit_code == 0
    assert "Using 1 context file" in result.output
    mock_execute.assert_awaited_once()


@patch("jitsu.cli.main.JitsuOrchestrator", autospec=True)
def test_cli_plan_default_path(
    mock_orch_cls: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that plan uses epics/current/{epic_id}.json by default."""
    monkeypatch.chdir(tmp_path)
    mock_orch = mock_orch_cls.return_value

    # Mock a directive with specific epic_id
    mock_directive = MagicMock(spec=AgentDirective)
    mock_directive.epic_id = "plan-epic-123"
    mock_orch.execute_plan = AsyncMock(return_value=[mock_directive])

    # Storage helper
    mock_orch.storage = EpicStorage(tmp_path)

    async def side_effect(
        _objective: str, _files: list[str], _out: Path, **_kwargs: object
    ) -> list[AgentDirective]:
        # Create the temp file
        await anyio.Path(_out).write_text("[]", encoding="utf-8")
        return [mock_directive]

    mock_orch.execute_plan.side_effect = side_effect

    result = runner.invoke(app, ["plan", "Some objective"])

    assert result.exit_code == 0
    expected_path = tmp_path / "epics" / "current" / "plan-epic-123.json"
    assert expected_path.exists()
    assert f"Plan successfully generated and saved to {expected_path}" in result.output


@patch("jitsu.cli.main.anyio.run")
def test_cli_queue_ls(mock_run: MagicMock) -> None:
    """Test the 'jitsu queue ls' command."""
    mock_run.return_value = "Phase: p1 (Epic: e1)"
    result = runner.invoke(app, ["queue", "ls"])
    assert result.exit_code == 0
    assert "Phase: p1 (Epic: e1)" in result.output


@patch("jitsu.cli.main.anyio.run")
def test_cli_queue_clear_success(mock_run: MagicMock) -> None:
    """Test the 'jitsu queue clear' command on success."""
    mock_run.return_value = "ACK. Queue cleared."
    result = runner.invoke(app, ["queue", "clear"])
    assert result.exit_code == 0
    assert "ACK. Queue cleared." in result.output


@patch("jitsu.cli.main.anyio.run")
def test_cli_queue_clear_error(mock_run: MagicMock) -> None:
    """Test the 'jitsu queue clear' command on failure."""
    mock_run.return_value = "ERR: Server down"
    result = runner.invoke(app, ["queue", "clear"])
    assert result.exit_code == 1
    assert "Server Error: ERR: Server down" in result.output


@patch("jitsu.cli.main.JitsuOrchestrator", autospec=True)
def test_cli_run_success(
    mock_orch_cls: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the 'jitsu run' command on success."""
    monkeypatch.chdir(tmp_path)
    mock_orch = mock_orch_cls.return_value
    mock_orch.execute_run = AsyncMock()

    # Trigger callback when execute_run is called
    async def side_effect(*_args: object, **_kwargs: object) -> None:
        on_progress = mock_orch_cls.call_args[1].get("on_progress")
        if on_progress:
            on_progress("Step 1 done")

    mock_orch.execute_run.side_effect = side_effect

    result = runner.invoke(app, ["run", "Build something"])

    assert result.exit_code == 0
    mock_orch.execute_run.assert_awaited_once()

    # Verify verbose flag is accepted
    result_v = runner.invoke(app, ["run", "Build something", "-v"])
    assert result_v.exit_code == 0


@patch.object(JitsuOrchestrator, "execute_run", new_callable=AsyncMock)
def test_cli_run_failure(
    mock_execute: AsyncMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the 'jitsu run' command on failure."""
    monkeypatch.chdir(tmp_path)
    mock_execute.side_effect = typer.Exit(1)

    result = runner.invoke(app, ["run", "Build something"])
    assert result.exit_code == 1
    mock_execute.assert_awaited_once()


def test_cli_init_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful initialization of a new project."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert "Created epics/current/ and epics/completed/." in result.output
    assert "Created .jitsurules with default protocol." in result.output
    assert "Created justfile with verify recipe." in result.output
    assert "Jitsu project initialized successfully!" in result.output

    assert (tmp_path / "epics" / "current").is_dir()
    assert (tmp_path / "epics" / "completed").is_dir()
    assert (tmp_path / ".jitsurules").is_file()
    assert (tmp_path / "justfile").is_file()

    # Verify content includes new protocol elements
    rules_content = (tmp_path / ".jitsurules").read_text(encoding="utf-8")
    assert "jitsu_git_status" in rules_content
    assert "jitsu_git_commit" in rules_content
    assert "self-orchestration" in rules_content.lower()


def test_cli_init_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that init does not overwrite existing files."""
    monkeypatch.chdir(tmp_path)

    # Pre-create files
    rules = tmp_path / ".jitsurules"
    rules.write_text("existing rules", encoding="utf-8")

    justfile = tmp_path / "justfile"
    justfile.write_text("existing justfile", encoding="utf-8")

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert ".jitsurules already exists, skipping." in result.output
    assert "justfile already exists, skipping." in result.output

    assert rules.read_text(encoding="utf-8") == "existing rules"
    assert justfile.read_text(encoding="utf-8") == "existing justfile"


def test_cli_init_skips_justfile_capital(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that init skips justfile creation if 'Justfile' exists."""
    monkeypatch.chdir(tmp_path)
    content = "existing Justfile"
    (tmp_path / "Justfile").write_text(content, encoding="utf-8")

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "justfile already exists, skipping." in result.output
    # Check that we didn't overwrite it or create a lowercase one if possible
    assert (tmp_path / "Justfile").read_text(encoding="utf-8") == content


def test_cli_init_os_error_mkdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of directory creation failure."""
    monkeypatch.chdir(tmp_path)

    with patch("jitsu.cli.main.Path.mkdir", side_effect=OSError("Permission denied")):
        result = runner.invoke(app, ["init"])

    assert result.exit_code == 1
    assert "Failed to create directories: Permission denied" in result.output


def test_cli_init_os_error_write_rules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of .jitsurules write failure."""
    monkeypatch.chdir(tmp_path)

    with patch("jitsu.cli.main.Path.write_text", side_effect=OSError("Write error")):
        result = runner.invoke(app, ["init"])

    assert result.exit_code == 1
    assert "Failed to create .jitsurules: Write error" in result.output


def test_cli_init_os_error_write_justfile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of justfile write failure."""
    monkeypatch.chdir(tmp_path)

    # First call (.jitsurules) succeeds, second call (justfile) fails
    with patch("jitsu.cli.main.Path.write_text", side_effect=[100, OSError("Write error")]):
        result = runner.invoke(app, ["init"])

    assert result.exit_code == 1
    assert "Failed to create justfile: Write error" in result.output


def test_cli_init_resource_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of template loading failure."""
    monkeypatch.chdir(tmp_path)

    with patch(
        "jitsu.cli.main.TemplateLoader.load_template", side_effect=OSError("Resource error")
    ):
        result = runner.invoke(app, ["init"])

    assert result.exit_code == 1
    assert "Failed to load templates from resources: Resource error" in result.output


@patch.object(JitsuOrchestrator, "execute_auto", new_callable=AsyncMock)
def test_cli_auto_success(
    mock_execute: AsyncMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the 'jitsu auto' command on success."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["auto", "Build something"])

    assert result.exit_code == 0
    mock_execute.assert_awaited_once()


@patch.object(JitsuOrchestrator, "execute_auto", new_callable=AsyncMock)
def test_cli_auto_failure(
    mock_execute: AsyncMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the 'jitsu auto' command when execution fails."""
    monkeypatch.chdir(tmp_path)
    mock_execute.side_effect = typer.Exit(1)

    result = runner.invoke(app, ["auto", "Build something"])

    assert result.exit_code == 1
    mock_execute.assert_awaited_once()


def test_cli_auto_missing_args() -> None:
    """Test 'jitsu auto' fails if neither objective nor --file is provided."""
    result = runner.invoke(app, ["auto"])
    assert result.exit_code == 1
    assert "Either an objective or a --file must be provided" in result.output


@patch.object(JitsuOrchestrator, "execute_auto", new_callable=AsyncMock)
def test_cli_auto_with_context(
    mock_execute: AsyncMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 'jitsu auto' passes context files to the planner."""
    monkeypatch.chdir(tmp_path)
    ctx_file = tmp_path / "context.py"
    ctx_file.touch()

    runner.invoke(app, ["auto", "test", "--context", str(ctx_file)])
    mock_execute.assert_awaited_once()
    # Check that ctx_file was in the context argument
    args, _ = mock_execute.call_args
    # objective, file, context, model, verbose
    assert ctx_file in args[2]
