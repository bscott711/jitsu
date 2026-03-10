"""Tests for the Jitsu IPC server."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from anyio.abc import SocketStream

from jitsu.core.state import JitsuStateManager
from jitsu.server.ipc import IPCServer


@pytest.fixture
def state_manager() -> JitsuStateManager:
    """Fixture to provide a clean state manager."""
    return JitsuStateManager()


@pytest.fixture
def ipc_server(state_manager: JitsuStateManager) -> IPCServer:
    """Fixture to provide an IPCServer instance."""
    return IPCServer(state_manager=state_manager)


@pytest.mark.asyncio
async def test_handle_client_success(
    ipc_server: IPCServer, state_manager: JitsuStateManager
) -> None:
    """Test successful handling of a client connection with valid directive data."""
    mock_client = AsyncMock(spec=SocketStream)
    directive_data = {
        "epic_id": "test-epic",
        "phase_id": "phase-1",
        "module_scope": "test",
        "instructions": "do something",
    }
    payload = json.dumps([directive_data]).encode("utf-8")
    mock_client.receive.return_value = payload

    await ipc_server.handle_client(mock_client)

    directive = state_manager.get_next_directive()
    assert directive is not None
    assert directive.epic_id == "test-epic"
    mock_client.receive.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_json_error(ipc_server: IPCServer) -> None:
    """Test handling of invalid JSON data from a client."""
    mock_client = AsyncMock(spec=SocketStream)
    mock_client.receive.return_value = b"invalid json"

    with patch("jitsu.server.ipc.logger") as mock_logger:
        await ipc_server.handle_client(mock_client)
        mock_logger.exception.assert_called_with("IPC Error: Received invalid JSON payload.")


@pytest.mark.asyncio
async def test_handle_client_validation_error(ipc_server: IPCServer) -> None:
    """Test handling of data that fails Pydantic validation."""
    mock_client = AsyncMock(spec=SocketStream)
    # Missing required fields like phase_id
    mock_client.receive.return_value = json.dumps([{"epic_id": "test-epic"}]).encode("utf-8")

    with patch("jitsu.server.ipc.logger") as mock_logger:
        await ipc_server.handle_client(mock_client)
        mock_logger.exception.assert_called_with("IPC Error: Invalid epic schema")


@pytest.mark.asyncio
async def test_handle_client_unexpected_error(ipc_server: IPCServer) -> None:
    """Test handling of unexpected errors during client communication."""
    mock_client = AsyncMock(spec=SocketStream)
    mock_client.receive.side_effect = Exception("Boom")

    with patch("jitsu.server.ipc.logger") as mock_logger:
        await ipc_server.handle_client(mock_client)
        mock_logger.exception.assert_called_with("IPC Error: Unexpected error handling payload")


@pytest.mark.asyncio
async def test_ipc_serve(ipc_server: IPCServer) -> None:
    """Test starting the IPC server listener."""
    with patch(
        "jitsu.server.ipc.anyio.create_tcp_listener", new_callable=AsyncMock
    ) as mock_listener:
        mock_server = AsyncMock()
        mock_listener.return_value = mock_server

        await ipc_server.serve()

        mock_listener.assert_called_once_with(local_host="127.0.0.1", local_port=ipc_server.port)
        mock_server.serve.assert_called_once_with(ipc_server.handle_client)
