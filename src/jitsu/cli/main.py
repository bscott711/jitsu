"""Command Line Interface main entry point for Jitsu."""

import sys
from functools import partial
from pathlib import Path
from typing import Annotated

import anyio
import typer
from pydantic import TypeAdapter, ValidationError

from jitsu.config import settings
from jitsu.core.orchestrator import JitsuOrchestrator
from jitsu.core.storage import EpicStorage
from jitsu.models.core import AgentDirective
from jitsu.server.client import send_payload
from jitsu.server.mcp_server import run_server, state_manager
from jitsu.templates.loader import TemplateLoader

app = typer.Typer(
    name="jitsu",
    help="Jitsu: JIT Context & Workflow Orchestrator for AI IDEs",
    no_args_is_help=True,
)

queue_app = typer.Typer(help="Manage the Jitsu execution queue.")
app.add_typer(queue_app, name="queue")


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
        storage = EpicStorage()
        try:
            content = storage.read_text(epic)
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
    except (OSError, RuntimeError) as e:
        typer.secho(
            f"\n❌ Fatal error during server execution: {e}",
            fg=typer.colors.RED,
            bold=True,
            err=True,
        )
        sys.exit(1)


@app.command()
def init() -> None:
    """Scaffold a new Jitsu project in the current working directory."""
    cwd = Path.cwd()

    # Load templates from resources
    try:
        rules_template = TemplateLoader.load_template("rules.md")
        justfile_template = TemplateLoader.load_template("justfile.tmpl")
    except OSError as e:
        typer.secho(
            f"❌ Failed to load templates from resources: {e}", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(1) from e

    # 1. Create directories
    epics_dir = cwd / "epics"
    current_dir = epics_dir / "current"
    completed_dir = epics_dir / "completed"

    try:
        current_dir.mkdir(parents=True, exist_ok=True)
        completed_dir.mkdir(parents=True, exist_ok=True)
        typer.secho(
            "✅ Created epics/current/ and epics/completed/.", fg=typer.colors.GREEN, err=True
        )
    except OSError as e:
        typer.secho(f"❌ Failed to create directories: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from e

    # 2. Create .jitsurules
    rules_path = cwd / ".jitsurules"
    if rules_path.exists():
        typer.secho("⏩ .jitsurules already exists, skipping.", fg=typer.colors.YELLOW, err=True)
    else:
        try:
            rules_path.write_text(rules_template, encoding="utf-8")
            typer.secho(
                "✅ Created .jitsurules with default protocol.", fg=typer.colors.GREEN, err=True
            )
        except OSError as e:
            typer.secho(f"❌ Failed to create .jitsurules: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1) from e

    # 3. Create justfile (check for Justfile or justfile)
    justfile_path = cwd / "justfile"
    justfile_alt_path = cwd / "Justfile"

    if justfile_path.exists() or justfile_alt_path.exists():
        typer.secho("⏩ justfile already exists, skipping.", fg=typer.colors.YELLOW, err=True)
    else:
        try:
            justfile_path.write_text(justfile_template, encoding="utf-8")
            typer.secho("✅ Created justfile with verify recipe.", fg=typer.colors.GREEN, err=True)
        except OSError as e:
            typer.secho(f"❌ Failed to create justfile: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1) from e

    typer.secho(
        "\n✨ Jitsu project initialized successfully!", fg=typer.colors.GREEN, bold=True, err=True
    )


@app.command()
def submit(
    epic: Annotated[
        Path, typer.Option("--epic", "-e", help="Path to the epic JSON file.", exists=True)
    ],
) -> None:
    """Submit a new epic payload to a running Jitsu server."""
    storage = EpicStorage()
    try:
        payload = storage.read_bytes(epic)
        response = anyio.run(send_payload, payload)

        if response.startswith("ACK"):
            typer.secho(f"✅ {response}", fg=typer.colors.GREEN, err=True)

            # Auto-archive the epic file
            dest = storage.archive(epic)

            typer.secho(
                f"📂 Epic archived to {storage.completed_rel(dest)}",
                fg=typer.colors.CYAN,
                err=True,
            )
        else:
            typer.secho(f"❌ Server Error: {response}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

    except OSError as e:
        typer.secho(f"❌ Failed to read epic file: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from e


@queue_app.command("ls")
def queue_ls() -> None:
    """List all pending phases in the Jitsu queue."""
    response = anyio.run(send_payload, b"QUEUE_LS")
    typer.echo(response)


@queue_app.command("clear")
def queue_clear() -> None:
    """Clear all pending phases from the Jitsu queue."""
    response = anyio.run(send_payload, b"QUEUE_CLEAR")
    if response.startswith("ACK"):
        typer.secho(f"✅ {response}", fg=typer.colors.GREEN, err=True)
    else:
        typer.secho(f"❌ Server Error: {response}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def plan(
    objective: Annotated[str, typer.Argument(help="The natural language objective for the epic.")],
    *,
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
        Path | None,
        typer.Option("--out", "-o", help="Output path for the generated epic JSON."),
    ] = None,
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help="The LLM model to use via OpenRouter.",
        ),
    ] = settings.planner_model,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose debug output.")
    ] = False,
) -> None:
    """Generate a Jitsu plan from a natural language objective."""
    file_strings = [str(f) for f in files] if files else []

    typer.secho(f"🧠 Generating plan for: '{objective}'", fg=typer.colors.CYAN, err=True)
    typer.secho(f"🤖 Using model: {model}", fg=typer.colors.CYAN, err=True)
    if file_strings:
        typer.secho(
            f"📎 Using {len(file_strings)} context file(s).", fg=typer.colors.CYAN, err=True
        )

    def on_progress(msg: str) -> None:
        typer.secho(f"  {msg}", fg=typer.colors.WHITE, dim=True, err=True)

    orchestrator = JitsuOrchestrator(on_progress=on_progress)
    actual_out = out or Path("temp_plan.json")

    directives = anyio.run(
        partial(
            orchestrator.execute_plan,
            objective,
            file_strings,
            actual_out,
            model=model,
            verbose=verbose,
        )
    )

    if out is None:
        epic_id = directives[0].epic_id
        out = orchestrator.storage.get_current_path(epic_id)
        actual_out.replace(out)
    else:
        out = actual_out

    typer.secho(
        f"\n✅ Plan successfully generated and saved to {out}",
        fg=typer.colors.GREEN,
        bold=True,
        err=True,
    )


@app.command()
def run(
    objective: Annotated[str, typer.Argument(help="The natural language objective for the epic.")],
    *,
    files: Annotated[
        list[Path] | None,
        typer.Option(
            "--file",
            "-f",
            help="Relevant files to provide as context (can be used multiple times).",
            exists=True,
        ),
    ] = None,
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help="The LLM model to use via OpenRouter.",
        ),
    ] = settings.planner_model,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose debug output.")
    ] = False,
) -> None:
    """Generate a Jitsu plan and immediately submit it to the server."""
    file_strings = [str(f) for f in files] if files else []
    orchestrator = JitsuOrchestrator()
    anyio.run(
        partial(orchestrator.execute_run, objective, file_strings, model=model, verbose=verbose)
    )


@app.command()
def auto(
    objective: Annotated[
        str | None, typer.Argument(help="The natural language objective for the epic.")
    ] = None,
    *,
    file: Annotated[
        Path | None,
        typer.Option(
            "--file",
            "-f",
            help="Load an existing Epic JSON file to resume execution.",
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
    context: Annotated[
        list[Path] | None,
        typer.Option(
            "--context",
            "-c",
            help="Relevant files to provide as context (can be used multiple times).",
            exists=True,
        ),
    ] = None,
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help="The LLM model to use via OpenRouter.",
        ),
    ] = settings.planner_model,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose debug output.")
    ] = False,
) -> None:
    """Generate a Jitsu plan and execute it autonomously step-by-step."""
    if not objective and not file:
        typer.secho(
            "❌ Either an objective or a --file must be provided.",
            fg=typer.colors.RED,
            bold=True,
            err=True,
        )
        raise typer.Exit(1)

    orchestrator = JitsuOrchestrator()
    anyio.run(
        partial(orchestrator.execute_auto, objective, file, context, model=model, verbose=verbose)
    )


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
