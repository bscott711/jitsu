"""Command Line Interface main entry point for Jitsu."""

import sys
from pathlib import Path
from typing import Annotated

import anyio
import typer
from pydantic import TypeAdapter, ValidationError

from jitsu.models.core import AgentDirective
from jitsu.server.mcp_server import run_server, state_manager

app = typer.Typer(
    name="jitsu",
    help="Jitsu: JIT Context & Workflow Orchestrator for AI IDEs",
    no_args_is_help=True,
)


@app.callback()
def main_callback() -> None:
    """Jitsu CLI."""


@app.command()
def serve(
    epic: Annotated[
        Path | None,
        typer.Option(
            "--epic",
            "-e",
            help="Path to a JSON Epic plan to preload into the queue.",
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
) -> None:
    """Start the Jitsu MCP Server over stdio."""
    if epic:
        typer.secho(
            f"📦 Loading Epic plan from {epic.name}...",
            fg=typer.colors.CYAN,
            err=True,
        )
        try:
            content = epic.read_text(encoding="utf-8")
            adapter = TypeAdapter(list[AgentDirective])
            directives = adapter.validate_json(content)

            for directive in directives:
                state_manager.queue_directive(directive)

            typer.secho(
                f"✅ Successfully queued {len(directives)} phase(s).",
                fg=typer.colors.GREEN,
                bold=True,
                err=True,
            )
        except ValidationError as e:
            typer.secho(
                f"\n❌ Validation Error parsing {epic.name}:\n{e}",
                fg=typer.colors.RED,
                bold=True,
                err=True,
            )
            raise typer.Exit(1) from e
        except OSError as e:
            typer.secho(
                f"\n❌ Failed to read {epic.name}: {e}",
                fg=typer.colors.RED,
                bold=True,
                err=True,
            )
            raise typer.Exit(1) from e

    typer.secho(
        "⚡ Starting Jitsu MCP Server...",
        fg=typer.colors.GREEN,
        bold=True,
        err=True,
    )
    typer.secho(
        "📡 Listening for IDE agent connections on stdio...",
        fg=typer.colors.CYAN,
        err=True,
    )

    try:
        anyio.run(run_server)
    except KeyboardInterrupt:
        typer.secho(
            "\n🛑 Shutting down Jitsu MCP Server...",
            fg=typer.colors.YELLOW,
            bold=True,
            err=True,
        )
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        typer.secho(
            f"\n❌ Fatal error during server execution: {e}",
            fg=typer.colors.RED,
            bold=True,
            err=True,
        )
        sys.exit(1)


async def _send_payload(payload: bytes, port: int = 8765) -> None:
    """Async helper to send the payload over TCP."""
    try:
        async with await anyio.connect_tcp("127.0.0.1", port) as client:
            await client.send(payload)
    except ConnectionRefusedError as e:
        typer.secho(
            "❌ Connection refused. Is the Jitsu server running?", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(1) from e


@app.command()
def submit(
    epic: Annotated[
        Path, typer.Option("--epic", "-e", help="Path to the epic JSON file.", exists=True)
    ],
) -> None:
    """Submit a new epic payload to a running Jitsu server."""
    try:
        payload = epic.read_bytes()
        anyio.run(_send_payload, payload)
        typer.secho(
            f"✅ Successfully submitted {epic.name} to running server.",
            fg=typer.colors.GREEN,
            err=True,
        )
    except OSError as e:
        typer.secho(f"❌ Failed to read epic file: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from e


async def _run_planner(objective: str, files: list[str], out: Path) -> None:
    """Async helper to run the planner and save the output."""
    from jitsu.core.planner import JitsuPlanner  # noqa: PLC0415

    planner = JitsuPlanner(objective=objective, relevant_files=files)
    directives = await planner.generate_plan()

    if not directives:
        typer.secho(
            "❌ Planner failed to generate valid directives.", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(1)

    planner.save_plan(out)


@app.command()
def plan(
    objective: Annotated[str, typer.Argument(help="The natural language objective for the epic.")],
    files: Annotated[
        list[Path] | None,
        typer.Option(
            "--file",
            "-f",
            help="Relevant files to provide as context (can be used multiple times).",
            exists=True,
        ),
    ] = None,
    out: Annotated[
        Path, typer.Option("--out", "-o", help="Output path for the generated epic JSON.")
    ] = Path("epic.json"),
) -> None:
    """Generate a Jitsu plan from a natural language objective."""
    file_strings = [str(f) for f in files] if files else []

    typer.secho(f"🧠 Generating plan for: '{objective}'", fg=typer.colors.CYAN, err=True)
    if file_strings:
        typer.secho(
            f"📎 Using {len(file_strings)} context file(s).", fg=typer.colors.CYAN, err=True
        )

    with typer.progressbar(length=100, label="Pondering...") as progress:
        # We run the planner. (Note: progress bar is just visual UX here since LLM calls are opaque in duration)
        anyio.run(_run_planner, objective, file_strings, out)
        progress.update(100)

    typer.secho(
        f"\n✅ Plan successfully generated and saved to {out}",
        fg=typer.colors.GREEN,
        bold=True,
        err=True,
    )


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
