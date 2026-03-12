"""Inter-process communication (IPC) server for Jitsu."""

import json

import anyio
from anyio.abc import SocketStream
from pydantic import ValidationError

from jitsu.core.state import JitsuStateManager
from jitsu.models.core import AgentDirective
from jitsu.utils.logger import get_logger

logger = get_logger("ipc")


class IPCServer:
    """Background TCP server that receives epics and appends them to the queue."""

    def __init__(self, state_manager: JitsuStateManager, port: int = 8765) -> None:
        """Initialize the IPC server with a state manager and port."""
        self.state_manager = state_manager
        self.port = port

    async def _handle_command(self, client: SocketStream, payload: str) -> bool:
        """Handle raw string commands. Returns True if handled, False otherwise."""
        if payload == "QUEUE_LS":
            pending = self.state_manager.get_pending_phases()
            if not pending:
                await client.send(b"Queue is empty.")
            else:
                lines = [f"Phase: {p['phase_id']} (Epic: {p['epic_id']})" for p in pending]
                await client.send("\n".join(lines).encode())
            return True

        if payload == "QUEUE_CLEAR":
            self.state_manager.clear_queue()
            await client.send(b"ACK. Queue cleared.")
            return True

        return False

    async def _process_json_payload(self, client: SocketStream, payload: str) -> None:
        """Parse JSON and queue incoming directives."""
        epics_data = json.loads(payload)
        count = 0

        for item in epics_data:
            directive = AgentDirective.model_validate(item)
            self.state_manager.queue_directive(directive)
            count += 1

        logger.info("IPC: Successfully received and queued %d phase(s).", count)
        await client.send(f"ACK: Queued {count} phase(s).".encode())

    async def handle_client(self, client: SocketStream) -> None:
        """Handle incoming connections and parse the epic payload."""
        async with client:
            try:
                chunks: list[bytes] = [chunk async for chunk in client]
                if not chunks:
                    return

                payload = b"".join(chunks).decode("utf-8").strip()

                if await self._handle_command(client, payload):
                    return

                await self._process_json_payload(client, payload)

            except json.JSONDecodeError as e:
                logger.exception("IPC Error: Received invalid JSON payload.")
                await client.send(f"ERR: Invalid JSON - {e}".encode())
            except ValidationError as e:
                logger.exception("IPC Error: Invalid epic schema")
                await client.send(f"ERR: Invalid Schema - {e}".encode())
            except Exception as e:
                logger.exception("IPC Error: Unexpected error handling payload")
                await client.send(f"ERR: Unexpected Error - {e}".encode())

    async def serve(self) -> None:
        """Start the background TCP listener."""
        logger.info("Starting IPC daemon on port %d...", self.port)
        listener = await anyio.create_tcp_listener(local_host="127.0.0.1", local_port=self.port)
        await listener.serve(self.handle_client)
