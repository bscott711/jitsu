"""Tests for the Jitsu MCP server."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

from jitsu.models.core import AgentDirective
from jitsu.server.mcp_server import handle_call_tool, handle_list_tools, run_server, state_manager

EXPECTED_TOOL_COUNT = 4


@pytest.mark.asyncio
async def test_list_tools() -> None:
    """Test that the server lists the correct tools."""
    tools = await handle_list_tools()
    assert len(tools) == EXPECTED_TOOL_COUNT
    names = [tool.name for tool in tools]
    assert "jitsu_get_next_phase" in names
    assert "jitsu_report_status" in names
    assert "jitsu_request_context" in names
    assert "jitsu_inspect_queue" in names


@pytest.mark.asyncio
async def test_get_next_phase_empty() -> None:
    """Test getting a phase when the queue is empty."""
    while state_manager.get_next_directive():
        pass

    result = await handle_call_tool("jitsu_get_next_phase", {})
    assert isinstance(result[0], TextContent)
    assert result[0].text == "No pending phases in the queue."


@pytest.mark.asyncio
async def test_get_next_phase_with_data() -> None:
    """Test getting a phase when data exists in the queue."""
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="src/test",
        instructions="Do a thing",
    )
    state_manager.queue_directive(directive)

    result = await handle_call_tool("jitsu_get_next_phase", {})
    assert isinstance(result[0], TextContent)
    assert "phase-1" in result[0].text


@pytest.mark.asyncio
async def test_report_status_success() -> None:
    """Test reporting a successful status."""
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-success",
        module_scope="src/test",
        instructions="Test",
    )
    state_manager.queue_directive(directive)
    state_manager.get_next_directive()  # Pop it so it's "running" and remaining=0

    result = await handle_call_tool(
        "jitsu_report_status", {"phase_id": "phase-success", "status": "SUCCESS"}
    )
    assert isinstance(result[0], TextContent)
    assert "ACK. 0 phases remaining." in result[0].text
    assert state_manager.completed_reports[-1].phase_id == "phase-success"


@pytest.mark.asyncio
async def test_report_status_failed() -> None:
    """Test reporting a failed status (hits line 132)."""
    result = await handle_call_tool(
        "jitsu_report_status", {"phase_id": "phase-fail", "status": "FAILED"}
    )
    assert isinstance(result[0], TextContent)
    assert "Successfully recorded status FAILED" in result[0].text


@pytest.mark.asyncio
async def test_inspect_queue_empty() -> None:
    """Test inspecting an empty queue (hits line 143)."""
    while state_manager.get_next_directive():
        pass
    result = await handle_call_tool("jitsu_inspect_queue", {})
    assert isinstance(result[0], TextContent)
    assert "The queue is currently empty." in result[0].text


@pytest.mark.asyncio
async def test_inspect_queue() -> None:
    """Test inspecting the queue."""
    # Clear queue first (roughly, by popping)
    while state_manager.get_next_directive():
        pass

    directive = AgentDirective(
        epic_id="epic-inspect",
        phase_id="phase-inspect",
        module_scope="src/test",
        instructions="Test",
    )
    state_manager.queue_directive(directive)

    result = await handle_call_tool("jitsu_inspect_queue", {})
    assert isinstance(result[0], TextContent)
    assert "phase-inspect" in result[0].text
    assert "epic-inspect" in result[0].text


@pytest.mark.asyncio
async def test_report_status_missing_args() -> None:
    """Test reporting status with missing arguments."""
    result = await handle_call_tool("jitsu_report_status", None)
    assert isinstance(result[0], TextContent)
    assert "Error: Missing arguments." in result[0].text


@pytest.mark.asyncio
async def test_report_status_invalid() -> None:
    """Test reporting an invalid status (Pydantic validation catch)."""
    result = await handle_call_tool(
        "jitsu_report_status", {"phase_id": "phase-1", "status": "INVALID_STATUS"}
    )
    assert isinstance(result[0], TextContent)
    assert "Validation Error" in result[0].text


@pytest.mark.asyncio
async def test_unknown_tool() -> None:
    """Test calling an unknown tool throws a clean error."""
    with pytest.raises(ValueError, match="Unknown tool: unknown_tool"):
        await handle_call_tool("unknown_tool", {})


@pytest.mark.asyncio
async def test_request_context_success() -> None:
    """Test successful JIT context request."""
    # We'll use a real file to test the FileStateProvider
    result = await handle_call_tool(
        "jitsu_request_context",
        {"target_identifier": "pyproject.toml", "provider_name": "file"},
    )
    assert isinstance(result[0], TextContent)
    # FileStateProvider returns content or "not found"
    assert "not found" in result[0].text or "[" in result[0].text


@pytest.mark.asyncio
async def test_request_context_missing_args() -> None:
    """Test context request with missing arguments."""
    result = await handle_call_tool("jitsu_request_context", {})
    assert isinstance(result[0], TextContent)
    assert "Error: Missing target_identifier" in result[0].text


@pytest.mark.asyncio
async def test_request_context_unknown_provider() -> None:
    """Test context request with an unknown provider."""
    result = await handle_call_tool(
        "jitsu_request_context",
        {"target_identifier": "test", "provider_name": "unknown"},
    )
    assert isinstance(result[0], TextContent)
    assert "Error: Unknown provider 'unknown'" in result[0].text


@pytest.mark.asyncio
async def test_request_context_mocked_ast() -> None:
    """Test correctly routing an AST request with mocked provider."""
    # Patch the class in mcp_server so when it instantiates, we control it
    with patch("jitsu.server.mcp_server.ASTProvider") as mock_cls:
        mock_instance = mock_cls.return_value
        mock_instance.resolve = AsyncMock(return_value="## AST OUTPUT")

        result = await handle_call_tool(
            "jitsu_request_context",
            {"target_identifier": "src/main.py", "provider_name": "ast"},
        )

        assert isinstance(result[0], TextContent)
        assert result[0].text == "## AST OUTPUT"
        mock_instance.resolve.assert_called_once_with("src/main.py")


@pytest.mark.asyncio
async def test_request_context_mocked_pydantic() -> None:
    """Test correctly routing a Pydantic request with mocked provider."""
    with patch("jitsu.server.mcp_server.PydanticProvider") as mock_cls:
        mock_instance = mock_cls.return_value
        mock_instance.resolve = AsyncMock(return_value="## PYDANTIC OUTPUT")

        result = await handle_call_tool(
            "jitsu_request_context",
            {"target_identifier": "User", "provider_name": "pydantic"},
        )

        assert isinstance(result[0], TextContent)
        assert result[0].text == "## PYDANTIC OUTPUT"
        mock_instance.resolve.assert_called_once_with("User")


@patch("jitsu.server.mcp_server.mcp.server.stdio.stdio_server")
@patch("jitsu.server.mcp_server.app.run")
@pytest.mark.asyncio
async def test_run_server(mock_run: MagicMock, mock_stdio: MagicMock) -> None:
    """Test the server runner initialization."""

    @asynccontextmanager
    async def mock_ctx() -> AsyncGenerator[tuple[str, str], None]:
        yield ("read", "write")

    mock_stdio.return_value = mock_ctx()

    await run_server()
    mock_run.assert_called_once()
