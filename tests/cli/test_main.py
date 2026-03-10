"""Tests for the Jitsu CLI main module."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pytest
import typer
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
def test_cli_submit_success(mock_run: MagicMock, tmp_path: Path) -> None:
    """Test successful epic submission via CLI."""
    epic_file = tmp_path / "epic.json"
    epic_file.write_text("[]", encoding="utf-8")

    mock_run.return_value = "ACK: Queued 0 phase(s)."

    result = runner.invoke(app, ["submit", "--epic", str(epic_file)])

    assert result.exit_code == 0
    assert "ACK: Queued 0 phase(s)." in result.output
    mock_run.assert_called_once()


@patch("jitsu.cli.main.anyio.run")
def test_cli_submit_server_error(mock_run: MagicMock, tmp_path: Path) -> None:
    """Test epic submission handles ERR: responses correctly."""
    epic_file = tmp_path / "epic.json"
    epic_file.write_text("[]", encoding="utf-8")

    mock_run.return_value = "ERR: Invalid Schema"

    result = runner.invoke(app, ["submit", "--epic", str(epic_file)])

    assert result.exit_code == 1
    assert "ERR: Invalid Schema" in result.output
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
    mock_generate.return_value = [
        AgentDirective(
            epic_id="test-epic",
            phase_id="p1",
            module_scope="test",
            instructions="test instructions",
        )
    ]
    out_file = tmp_path / "epic.json"

    result = runner.invoke(app, ["plan", "Build a cool feature", "--out", str(out_file)])

    assert result.exit_code == 0
    assert "Plan successfully generated" in result.output
    mock_generate.assert_awaited_once()
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
