"""Tests for the Jitsu CLI main module."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from jitsu.cli.main import _send_payload, app, main
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
    assert "Fatal error: Test mock error" in result.output


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
    with patch.object(Path, "read_text", side_effect=PermissionError("Access Denied")):
        result = runner.invoke(app, ["serve", "--epic", str(epic_file)])

    assert result.exit_code == 1
    mock_run.assert_not_called()
    assert "Failed to load" in result.output
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

    result = runner.invoke(app, ["submit", "--epic", str(epic_file)])

    assert result.exit_code == 0
    assert "Successfully submitted" in result.output
    mock_run.assert_called_once()


@patch("jitsu.cli.main.anyio.run", side_effect=Exception("Submit error"))
def test_cli_submit_failure(mock_run: MagicMock, tmp_path: Path) -> None:
    """Test epic submission failure handling."""
    epic_file = tmp_path / "epic.json"
    epic_file.write_text("[]", encoding="utf-8")

    result = runner.invoke(app, ["submit", "--epic", str(epic_file)])

    assert result.exit_code == 1
    assert "Failed to submit epic: Submit error" in result.output
    mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_send_payload_success() -> None:
    """Test internal _send_payload helper on success."""
    mock_client = AsyncMock()

    with patch("jitsu.cli.main.anyio.connect_tcp", (mock_connect := AsyncMock())):
        mock_connect.return_value.__aenter__.return_value = mock_client
        await _send_payload(b"test", port=1234)

        mock_connect.assert_called_once_with("127.0.0.1", 1234)
        mock_client.send.assert_called_once_with(b"test")


@pytest.mark.asyncio
async def test_send_payload_connection_refused() -> None:
    """Test _send_payload when the server connection is refused."""
    with patch("jitsu.cli.main.anyio.connect_tcp", side_effect=ConnectionRefusedError()):
        with pytest.raises(typer.Exit) as exc:
            await _send_payload(b"test")
        assert exc.value.exit_code == 1
