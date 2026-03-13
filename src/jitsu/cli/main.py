"""Command Line Interface main entry point for Jitsu."""

import sys
from pathlib import Path
from typing import Annotated

import anyio
import typer
from pydantic import TypeAdapter, ValidationError

from jitsu.core.storage import EpicStorage
from jitsu.models.core import AgentDirective
from jitsu.server.mcp_server import run_server, state_manager
from jitsu.utils.logger import secho as jitsu_secho
from jitsu.utils.logger import set_quiet

app = typer.Typer(
    name="jitsu",
    help="Jitsu: JIT Context & Workflow Orchestrator for AI IDEs",
    no_args_is_help=True,
)


@app.callback()
def main_callback(
    ctx: typer.Context,
    *,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress all non-error output.",
        ),
    ] = False,
) -> None:
    """Jitsu CLI."""
    ctx.ensure_object(dict)
    ctx.obj["quiet"] = quiet
    if quiet:
        set_quiet(enabled=True)


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
        jitsu_secho(
            f"📦 Loading Epic plan from {epic.name}...",
            fg=typer.colors.CYAN,
            err=True,
        )
        storage = EpicStorage()
        try:
            content = storage.read_text(epic)
            adapter = TypeAdapter(list[AgentDirective])
            directives = adapter.validate_json(content)

            for directive in directives:
                state_manager.queue_directive(directive)

            jitsu_secho(
                f"✅ Successfully queued {len(directives)} phase(s).",
                fg=typer.colors.GREEN,
                bold=True,
                err=True,
            )
        except ValidationError as e:
            jitsu_secho(
                f"\n❌ Validation Error parsing {epic.name}:\n{e}",
                fg=typer.colors.RED,
                bold=True,
                err=True,
            )
            raise typer.Exit(1) from e
        except OSError as e:
            jitsu_secho(
                f"\n❌ Failed to read {epic.name}: {e}",
                fg=typer.colors.RED,
                bold=True,
                err=True,
            )
            raise typer.Exit(1) from e

    jitsu_secho(
        "⚡ Starting Jitsu MCP Server...",
        fg=typer.colors.GREEN,
        bold=True,
        err=True,
    )
    jitsu_secho(
        "📡 Listening for IDE agent connections on stdio...",
        fg=typer.colors.CYAN,
        err=True,
    )

    try:
        anyio.run(run_server)
    except KeyboardInterrupt:
        jitsu_secho(
            "\n🛑 Shutting down Jitsu MCP Server...",
            fg=typer.colors.YELLOW,
            bold=True,
            err=True,
        )
        sys.exit(0)
    except (OSError, RuntimeError) as e:
        jitsu_secho(
            f"\n❌ Fatal error during server execution: {e}",
            fg=typer.colors.RED,
            bold=True,
            err=True,
        )
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
