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

    async def handle_client(self, client: SocketStream) -> None:
        """Handle incoming connections and parse the epic payload."""
        async with client:
            try:
                data = await client.receive(1024 * 1024)
                payload = data.decode("utf-8")

                epics_data = json.loads(payload)
                count = 0

                for item in epics_data:
                    directive = AgentDirective.model_validate(item)
                    self.state_manager.queue_directive(directive)
                    count += 1

                # G004 Fix: Lazy string interpolation
                logger.info("IPC: Successfully received and queued %d phase(s).", count)

            except json.JSONDecodeError:
                logger.exception("IPC Error: Received invalid JSON payload.")
            except ValidationError:
                # TRY401 Fix: Dropped 'as e' and the %s formatting
                logger.exception("IPC Error: Invalid epic schema")
            except Exception:
                # TRY401 Fix: Dropped 'as e' and the %s formatting
                logger.exception("IPC Error: Unexpected error handling payload")

    async def serve(self) -> None:
        """Start the background TCP listener."""
        # G004 Fix: Lazy string interpolation
        logger.info("Starting IPC daemon on port %d...", self.port)
        listener = await anyio.create_tcp_listener(local_host="127.0.0.1", local_port=self.port)
        await listener.serve(self.handle_client)
