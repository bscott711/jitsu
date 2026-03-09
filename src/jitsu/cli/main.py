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
            fg="cyan",
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
                fg="green",
                bold=True,
                err=True,
            )
        except ValidationError as e:
            typer.secho(
                f"\n❌ Validation Error parsing {epic.name}:\n{e}",
                fg="red",
                bold=True,
                err=True,
            )
            sys.exit(1)
        except Exception as e:  # noqa: BLE001
            typer.secho(
                f"\n❌ Failed to load {epic.name}: {e}",
                fg="red",
                bold=True,
                err=True,
            )
            sys.exit(1)

    typer.secho(
        "⚡ Starting Jitsu MCP Server...",
        fg="green",
        bold=True,
        err=True,
    )
    typer.secho(
        "📡 Listening for IDE agent connections on stdio...",
        fg="cyan",
        err=True,
    )

    try:
        anyio.run(run_server)
    except KeyboardInterrupt:
        typer.secho(
            "\n🛑 Shutting down Jitsu MCP Server...",
            fg="yellow",
            bold=True,
            err=True,
        )
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        typer.secho(
            f"\n❌ Fatal error: {e}",
            fg="red",
            bold=True,
            err=True,
        )
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
