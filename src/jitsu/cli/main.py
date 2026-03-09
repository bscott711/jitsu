"""Command Line Interface main entry point for Jitsu."""

import sys

import anyio
import typer

from jitsu.server.mcp_server import run_server

app = typer.Typer(
    name="jitsu",
    help="Jitsu: JIT Context & Workflow Orchestrator for AI IDEs",
    no_args_is_help=True,
)


@app.callback()
def main_callback() -> None:
    """Jitsu CLI."""
    # This empty callback forces Typer to retain the group structure
    # so that `jitsu serve` doesn't get collapsed into just `jitsu`.


@app.command()
def serve() -> None:
    """Start the Jitsu MCP Server over stdio."""
    # CRITICAL: MCP over stdio requires stdout to be strictly reserved for JSON-RPC.
    # All CLI informational output MUST go to stderr (err=True) to avoid corrupting the protocol.
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
