"""Tests for the Jitsu CLI main module."""

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import anyio
import httpx
import openai
import pytest
import typer
from instructor.core.exceptions import InstructorRetryException
from typer.testing import CliRunner

from jitsu.cli.main import _send_payload, app, main
from jitsu.models.core import AgentDirective
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


@patch("jitsu.cli.main.anyio.run", side_effect=Exception("Test mock error"))
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
            "module_scope": "test",
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
    with patch.object(Path, "read_text", side_effect=OSError("Access Denied")):
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


@patch.object(Path, "read_bytes", side_effect=OSError("Read error"))
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
    """Test internal _send_payload helper on success."""
    mock_client = AsyncMock()
    mock_client.receive.return_value = b"ACK: Queued 1 phase(s)."

    with patch("jitsu.cli.main.anyio.connect_tcp", (mock_connect := AsyncMock())):
        mock_connect.return_value.__aenter__.return_value = mock_client
        response = await _send_payload(b"test", port=1234)

        mock_connect.assert_called_once_with("127.0.0.1", 1234)
        mock_client.send.assert_called_once_with(b"test")
        mock_client.send_eof.assert_called_once()
        assert response == "ACK: Queued 1 phase(s)."


@pytest.mark.asyncio
async def test_send_payload_end_of_stream() -> None:
    """Test internal _send_payload helper handles EOF cleanly."""
    mock_client = AsyncMock()
    mock_client.receive.side_effect = anyio.EndOfStream()

    with patch("jitsu.cli.main.anyio.connect_tcp", (mock_connect := AsyncMock())):
        mock_connect.return_value.__aenter__.return_value = mock_client
        response = await _send_payload(b"test", port=1234)

        assert response == "ERR: Server closed connection without responding."


@pytest.mark.asyncio
async def test_send_payload_connection_refused() -> None:
    """Test _send_payload when the server connection is refused."""
    with patch("jitsu.cli.main.anyio.connect_tcp", side_effect=ConnectionRefusedError()):
        with pytest.raises(typer.Exit) as exc:
            await _send_payload(b"test")
        assert exc.value.exit_code == 1


@patch("jitsu.core.planner.JitsuPlanner.generate_plan")
@patch("jitsu.core.planner.JitsuPlanner.save_plan")
def test_cli_plan_success(mock_save: MagicMock, mock_generate: AsyncMock, tmp_path: Path) -> None:
    """Test successful plan generation via CLI."""

    async def mock_gen_side_effect(
        model: str, on_progress: Callable[[str], None] | None = None, *, verbose: bool = False
    ) -> list[AgentDirective]:
        del verbose  # Mark as used for Ruff
        if on_progress:
            on_progress(f"test progress using {model}")
        return [
            AgentDirective(
                epic_id="test-epic",
                phase_id="p1",
                module_scope="test",
                instructions="test instructions",
            )
        ]

    mock_generate.side_effect = mock_gen_side_effect
    out_file = tmp_path / "epic.json"

    result = runner.invoke(
        app, ["plan", "Build a cool feature", "--out", str(out_file), "-m", "gpt-4o"]
    )

    assert result.exit_code == 0
    assert "Plan successfully generated" in result.output
    assert "Using model: gpt-4o" in result.output
    assert "test progress using gpt-4o" in result.output
    mock_generate.assert_awaited_once_with(model="gpt-4o", on_progress=ANY, verbose=False)
    mock_save.assert_called_once_with(out_file)


@patch("jitsu.core.planner.JitsuPlanner.generate_plan")
def test_cli_plan_failure(mock_generate: AsyncMock, tmp_path: Path) -> None:
    """Test plan generation failure via CLI."""
    mock_generate.return_value = []
    out_file = tmp_path / "epic.json"

    result = runner.invoke(app, ["plan", "Build a cool feature", "--out", str(out_file)])

    assert result.exit_code == 1
    assert "Planner failed to generate valid directives" in result.output
    mock_generate.assert_awaited_once()


@patch("jitsu.core.planner.JitsuPlanner.generate_plan")
@patch("jitsu.core.planner.JitsuPlanner.save_plan")
def test_cli_plan_with_files(
    mock_save: MagicMock, mock_generate: AsyncMock, tmp_path: Path
) -> None:
    """Test plan generation with provided context files."""
    mock_generate.return_value = [
        AgentDirective(
            epic_id="test-epic",
            phase_id="p1",
            module_scope="test",
            instructions="test instructions",
        )
    ]
    out_file = tmp_path / "epic.json"
    ctx_file = tmp_path / "context_file.py"
    ctx_file.touch()

    result = runner.invoke(
        app, ["plan", "Feature", "--file", str(ctx_file), "--out", str(out_file)]
    )

    assert result.exit_code == 0
    assert "Using 1 context file" in result.output
    mock_generate.assert_awaited_once()
    mock_save.assert_called_once_with(out_file)


@patch("jitsu.core.planner.JitsuPlanner.generate_plan")
def test_cli_plan_runtime_error(mock_generate: AsyncMock, tmp_path: Path) -> None:
    """Test plan generation handles RuntimeError (e.g., missing API key) via CLI."""
    mock_generate.side_effect = RuntimeError("OPENROUTER_API_KEY environment variable is not set")
    out_file = tmp_path / "epic.json"

    result = runner.invoke(app, ["plan", "Build a cool feature", "--out", str(out_file)])

    assert result.exit_code == 1
    assert "Planner Error: OPENROUTER_API_KEY" in result.output
    assert "Tip: Ensure OPENROUTER_API_KEY is set" in result.output
    mock_generate.assert_awaited_once()


@patch("jitsu.core.planner.JitsuPlanner.generate_plan")
@patch("jitsu.core.planner.JitsuPlanner.save_plan")
def test_cli_plan_api_fallback_success(
    mock_save: MagicMock, mock_generate: AsyncMock, tmp_path: Path
) -> None:
    """Test that the planner successfully falls back to the backup model on a 429 error."""
    # Mock a 429 Rate Limit Response
    error_response = httpx.Response(429, request=httpx.Request("POST", "https://openrouter.ai"))
    mock_error = openai.APIStatusError("Rate limit exceeded", response=error_response, body=None)

    # First call raises the 429 error, second call returns the valid directives
    mock_generate.side_effect = [
        mock_error,
        [AgentDirective(epic_id="test", phase_id="p1", module_scope="test", instructions="test")],
    ]
    out_file = tmp_path / "epic.json"

    result = runner.invoke(
        app, ["plan", "test feature", "--out", str(out_file), "-m", "primary-model"]
    )

    assert result.exit_code == 0
    assert "API limit hit for primary-model" in result.output
    assert "Falling back to meta-llama/llama-3.3-70b-instruct:free" in result.output
    mock_save.assert_called_once_with(out_file)
    expected_calls = 2
    assert mock_generate.call_count == expected_calls


@patch("jitsu.core.planner.JitsuPlanner.generate_plan")
def test_cli_plan_api_status_error_fatal(mock_generate: AsyncMock, tmp_path: Path) -> None:
    """Test plan generation handles a fatal APIStatusError (e.g., a 500 Server Error)."""
    error_response = httpx.Response(500, request=httpx.Request("POST", "https://openrouter.ai"))
    mock_error = openai.APIStatusError("Internal Server Error", response=error_response, body=None)
    mock_generate.side_effect = mock_error
    out_file = tmp_path / "epic.json"

    result = runner.invoke(app, ["plan", "test feature", "--out", str(out_file)])

    assert result.exit_code == 1
    assert "OpenRouter API Error [500]: Internal Server Error" in result.output


@patch("jitsu.core.planner.JitsuPlanner.generate_plan")
def test_cli_plan_instructor_retry_error(mock_generate: AsyncMock, tmp_path: Path) -> None:
    """Test plan generation cleanly handles Instructor JSON validation failures."""
    # Pass a simple string to ensure the exception instantiates safely
    mock_generate.side_effect = InstructorRetryException(
        "mock_failure", n_attempts=3, total_usage=0
    )
    out_file = tmp_path / "epic.json"

    result = runner.invoke(app, ["plan", "test feature", "--out", str(out_file)])

    assert result.exit_code == 1
    assert "model failed to generate valid JSON matching the Jitsu schema" in result.output


@patch("jitsu.core.planner.JitsuPlanner.generate_plan")
def test_cli_plan_instructor_retry_error_verbose(mock_generate: AsyncMock, tmp_path: Path) -> None:
    """Test plan generation includes debug info on Instructor failure with --verbose."""
    e = InstructorRetryException("mock_failure", n_attempts=3, total_usage=0)
    cause = ValueError("Underlying cause")
    e.__cause__ = cause

    mock_generate.side_effect = e
    out_file = tmp_path / "epic.json"

    result = runner.invoke(app, ["plan", "test feature", "--out", str(out_file), "--verbose"])

    assert result.exit_code == 1
    assert "DEBUG: mock_failure" in result.output
    assert "CAUSE: Underlying cause" in result.output


@patch("jitsu.core.planner.JitsuPlanner.generate_plan")
def test_cli_plan_unexpected_exception(mock_generate: AsyncMock, tmp_path: Path) -> None:
    """Test plan generation safely catches unexpected blind exceptions."""
    # Use ValueError instead of a raw Exception so Pytest/AnyIO propagates it perfectly
    mock_generate.side_effect = ValueError("A wild cosmic ray flipped a bit.")
    out_file = tmp_path / "epic.json"

    result = runner.invoke(app, ["plan", "test feature", "--out", str(out_file)])

    assert result.exit_code == 1
    assert "Unexpected Error:" in result.output


@patch("jitsu.core.planner.JitsuPlanner.generate_plan")
def test_cli_plan_unexpected_exception_verbose(mock_generate: AsyncMock, tmp_path: Path) -> None:
    """Test plan generation includes debug info on unexpected failure with --verbose."""
    cause = ValueError("Cosmic ray")
    e = ValueError("A wild cosmic ray flipped a bit.")
    e.__cause__ = cause

    mock_generate.side_effect = e
    out_file = tmp_path / "epic.json"

    result = runner.invoke(app, ["plan", "test feature", "--out", str(out_file), "-v"])

    assert result.exit_code == 1
    assert "DEBUG: A wild cosmic ray flipped a bit." in result.output
    assert "CAUSE: Cosmic ray" in result.output


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


@patch("jitsu.cli.main.anyio.run")
def test_cli_run_success(
    mock_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the 'jitsu run' command on success."""
    monkeypatch.chdir(tmp_path)

    def run_side_effect(func: Any, *args: Any, **_kwargs: Any) -> Any:  # noqa: ANN401
        if func.__name__ == "_run_planner":
            out_path = args[2]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("[]", encoding="utf-8")
            return None
        if func.__name__ == "_send_payload":
            return "ACK: Queued 1 phase(s)."
        return None

    mock_run.side_effect = run_side_effect

    result = runner.invoke(app, ["run", "Build something"])

    assert result.exit_code == 0
    assert "Starting automated Jitsu pipeline" in result.output
    assert "Plan successfully generated" in result.output
    assert "Submitting plan to server" in result.output
    assert "ACK: Queued 1 phase(s)." in result.output
    assert "Pipeline complete. Epic archived" in result.output

    # Verify verbose flag is accepted
    result_v = runner.invoke(app, ["run", "Build something", "-v"])
    assert result_v.exit_code == 0


@patch("jitsu.cli.main.anyio.run")
def test_cli_run_planner_failure(
    mock_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the 'jitsu run' command when the planner fails."""
    monkeypatch.chdir(tmp_path)
    mock_run.side_effect = typer.Exit(1)

    result = runner.invoke(app, ["run", "Build something"])
    assert result.exit_code == 1


@patch("jitsu.cli.main.anyio.run")
def test_cli_run_submit_failure(
    mock_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the 'jitsu run' command when the server returns an error."""
    monkeypatch.chdir(tmp_path)

    def run_side_effect(func: Any, *args: Any, **_kwargs: Any) -> Any:  # noqa: ANN401
        if func.__name__ == "_run_planner":
            out_path = args[2]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("[]", encoding="utf-8")
            return None
        if func.__name__ == "_send_payload":
            return "ERR: Server down"
        return None

    mock_run.side_effect = run_side_effect

    result = runner.invoke(app, ["run", "Build something"])

    assert result.exit_code == 1
    assert "Server Error: ERR: Server down" in result.output


@patch("jitsu.cli.main.anyio.run")
def test_cli_run_os_error(
    mock_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the 'jitsu run' command handles OS errors (e.g., read failure)."""
    monkeypatch.chdir(tmp_path)

    def run_side_effect(func: Any, *args: Any, **_kwargs: Any) -> Any:  # noqa: ANN401
        if func.__name__ == "_run_planner":
            out_path = args[2]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("[]", encoding="utf-8")
            return None
        return None

    mock_run.side_effect = run_side_effect

    # We patch Path.read_bytes to raise OSError
    with patch.object(Path, "read_bytes", side_effect=OSError("Read error")):
        result = runner.invoke(app, ["run", "Build something"])

    assert result.exit_code == 1
    assert "Failed to read or move epic file: Read error" in result.output


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

    with patch("jitsu.cli.main.importlib.resources.files", side_effect=Exception("Resource error")):
        result = runner.invoke(app, ["init"])

    assert result.exit_code == 1
    assert "Failed to load templates from resources: Resource error" in result.output


@patch("jitsu.cli.main.anyio.run")
@patch("subprocess.run")
@patch("shutil.which")
def test_cli_auto_success(
    mock_which: MagicMock,
    mock_sub_run: MagicMock,
    mock_anyio_run: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the 'jitsu auto' command on success."""
    monkeypatch.chdir(tmp_path)
    mock_which.return_value = "/usr/bin/just"
    mock_sub_run.return_value = MagicMock(returncode=0)

    directive = AgentDirective(
        epic_id="test", phase_id="p1", module_scope="test", instructions="test"
    )

    def run_side_effect(func: Any, *args: Any, **_kwargs: Any) -> Any:  # noqa: ANN401
        if func.__name__ == "_run_planner":
            out_path = args[2]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("[]", encoding="utf-8")
            return [directive]
        if func.__name__ == "compile_directive":
            return "mock prompt"
        return None

    mock_anyio_run.side_effect = run_side_effect

    mock_executor = MagicMock()
    mock_executor.execute_directive.return_value = True

    mock_compiler = MagicMock()
    mock_compiler.compile_directive.__name__ = "compile_directive"

    with (
        patch("jitsu.cli.main.JitsuExecutor", return_value=mock_executor),
        patch("jitsu.cli.main.ContextCompiler", return_value=mock_compiler),
    ):
        result = runner.invoke(app, ["auto", "Build something"])

    assert result.exit_code == 0
    assert "Starting Autonomous Jitsu Execution" in result.output
    assert "Phase p1 completed" in result.output
    assert "Committing changes" in result.output
    assert "Autonomous execution complete" in result.output

    # Verify commit was called
    mock_sub_run.assert_called_once()
    assert mock_sub_run.call_args[0][0][0] == "/usr/bin/just"
    assert mock_sub_run.call_args[0][0][1] == "commit"


@patch("jitsu.cli.main.anyio.run")
def test_cli_auto_failure(
    mock_anyio_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the 'jitsu auto' command when execution fails."""
    monkeypatch.chdir(tmp_path)

    directive = AgentDirective(
        epic_id="test", phase_id="p1", module_scope="test", instructions="test"
    )

    def run_side_effect(func: Any, *args: Any, **_kwargs: Any) -> Any:  # noqa: ANN401
        if func.__name__ == "_run_planner":
            out_path = args[2]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("[]", encoding="utf-8")
            return [directive]
        if func.__name__ == "compile_directive":
            return "mock prompt"
        return None

    mock_anyio_run.side_effect = run_side_effect

    mock_executor = MagicMock()
    mock_executor.execute_directive.return_value = False

    mock_compiler = MagicMock()
    mock_compiler.compile_directive.__name__ = "compile_directive"

    with (
        patch("jitsu.cli.main.JitsuExecutor", return_value=mock_executor),
        patch("jitsu.cli.main.ContextCompiler", return_value=mock_compiler),
    ):
        result = runner.invoke(app, ["auto", "Build something"])

    assert result.exit_code == 1
    assert "Phase p1 failed to execute or verify" in result.output


@patch("jitsu.cli.main.anyio.run")
@patch("subprocess.run")
@patch("shutil.which")
def test_cli_auto_commit_failure(
    mock_which: MagicMock,
    mock_sub_run: MagicMock,
    mock_anyio_run: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the 'jitsu auto' command when the commit fails."""
    monkeypatch.chdir(tmp_path)
    mock_which.return_value = "/usr/bin/just"
    # Mock commit failure
    mock_sub_run.return_value = MagicMock(returncode=1, stderr="Commit error")

    directive = AgentDirective(
        epic_id="test", phase_id="p1", module_scope="test", instructions="test"
    )

    def run_side_effect(func: Any, *args: Any, **_kwargs: Any) -> Any:  # noqa: ANN401
        if func.__name__ == "_run_planner":
            out_path = args[2]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("[]", encoding="utf-8")
            return [directive]
        if func.__name__ == "compile_directive":
            return "mock prompt"
        return None

    mock_anyio_run.side_effect = run_side_effect

    mock_executor = MagicMock()
    mock_executor.execute_directive.return_value = True

    mock_compiler = MagicMock()
    mock_compiler.compile_directive.__name__ = "compile_directive"

    with (
        patch("jitsu.cli.main.JitsuExecutor", return_value=mock_executor),
        patch("jitsu.cli.main.ContextCompiler", return_value=mock_compiler),
    ):
        result = runner.invoke(app, ["auto", "Build something"])

    assert result.exit_code == 1
    assert "Commit failed: Commit error" in result.output


@patch("jitsu.cli.main.anyio.run")
@patch("shutil.which")
def test_cli_auto_just_missing(
    mock_which: MagicMock,
    mock_anyio_run: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the 'jitsu auto' command when 'just' is missing."""
    monkeypatch.chdir(tmp_path)
    mock_which.return_value = None

    directive = AgentDirective(
        epic_id="test", phase_id="p1", module_scope="test", instructions="test"
    )

    def run_side_effect(func: Any, *args: Any, **_kwargs: Any) -> Any:  # noqa: ANN401
        if func.__name__ == "_run_planner":
            out_path = args[2]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("[]", encoding="utf-8")
            return [directive]
        if func.__name__ == "compile_directive":
            return "mock prompt"
        return None

    mock_anyio_run.side_effect = run_side_effect

    mock_executor = MagicMock()
    mock_executor.execute_directive.return_value = True

    mock_compiler = MagicMock()
    mock_compiler.compile_directive.__name__ = "compile_directive"

    with (
        patch("jitsu.cli.main.JitsuExecutor", return_value=mock_executor),
        patch("jitsu.cli.main.ContextCompiler", return_value=mock_compiler),
    ):
        result = runner.invoke(app, ["auto", "Build something"])

    assert result.exit_code == 1
    assert "'just' executable not found in PATH" in result.output
