"""TCP client for communicating with the Jitsu IPC server."""

import anyio
import typer


async def send_payload(payload: bytes, port: int = 8765) -> str:
    """Async helper to send the payload over TCP and await response."""
    try:
        async with await anyio.connect_tcp("127.0.0.1", port) as client:
            await client.send(payload)
            await client.send_eof()  # Signal we are done writing so server can process

            try:
                response_data = await client.receive()
                return response_data.decode("utf-8").strip()
            except anyio.EndOfStream:
                return "ERR: Server closed connection without responding."

    except ConnectionRefusedError as e:
        typer.secho(
            "❌ Connection refused. Is the Jitsu server running?", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(1) from e
