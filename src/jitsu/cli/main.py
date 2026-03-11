"""Command Line Interface main entry point for Jitsu."""

import importlib.resources
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, cast

import anyio
import openai
import typer
from anyio.to_thread import run_sync
from instructor.core.exceptions import InstructorRetryException
from pydantic import TypeAdapter, ValidationError

from jitsu.core.compiler import ContextCompiler
from jitsu.core.executor import JitsuExecutor
from jitsu.core.storage import EpicStorage
from jitsu.models.core import AgentDirective
from jitsu.server.mcp_server import run_server, state_manager

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
    except Exception as e:  # noqa: BLE001
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
        rules_template = (
            importlib.resources.files("jitsu.templates")
            .joinpath("rules.md")
            .read_text(encoding="utf-8")
        )
        justfile_template = (
            importlib.resources.files("jitsu.templates")
            .joinpath("justfile.tmpl")
            .read_text(encoding="utf-8")
        )
    except Exception as e:
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


async def _send_payload(payload: bytes, port: int = 8765) -> str:
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
        response = anyio.run(_send_payload, payload)

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
    response = anyio.run(_send_payload, b"QUEUE_LS")
    typer.echo(response)


@queue_app.command("clear")
def queue_clear() -> None:
    """Clear all pending phases from the Jitsu queue."""
    response = anyio.run(_send_payload, b"QUEUE_CLEAR")
    if response.startswith("ACK"):
        typer.secho(f"✅ {response}", fg=typer.colors.GREEN, err=True)
    else:
        typer.secho(f"❌ Server Error: {response}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


def _handle_planner_error(e: Exception, verbose: bool = False) -> None:  # noqa: FBT001, FBT002
    """Handle planner errors and exit the CLI."""
    if isinstance(e, RuntimeError):
        typer.secho(f"\n❌ Planner Error: {e}", fg=typer.colors.RED, bold=True, err=True)
        if "OPENROUTER_API_KEY" in str(e):
            typer.secho(
                "💡 Tip: Ensure OPENROUTER_API_KEY is set in your environment or .env file.",
                fg=typer.colors.YELLOW,
                err=True,
            )
        raise typer.Exit(1) from None

    if isinstance(e, openai.APIStatusError):
        typer.secho(
            f"\n❌ OpenRouter API Error [{e.status_code}]: {e.message}",
            fg=typer.colors.RED,
            bold=True,
            err=True,
        )
        raise typer.Exit(1) from None

    if isinstance(e, InstructorRetryException):
        typer.secho(
            "\n❌ Planner Error: The model failed to generate valid JSON matching the Jitsu schema after multiple retries. Try a larger model.",
            fg=typer.colors.RED,
            bold=True,
            err=True,
        )
        if verbose:
            typer.secho(f"\nDEBUG: {e}", fg=typer.colors.YELLOW, err=True)
            if e.__cause__:
                typer.secho(f"CAUSE: {e.__cause__}", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(1) from None

    # Fallback for unexpected exceptions
    typer.secho(f"\n❌ Unexpected Error: {e}", fg=typer.colors.RED, bold=True, err=True)
    if verbose:
        typer.secho(f"\nDEBUG: {e}", fg=typer.colors.YELLOW, err=True)
        if hasattr(e, "__cause__") and e.__cause__:
            typer.secho(f"CAUSE: {e.__cause__}", fg=typer.colors.YELLOW, err=True)
    raise typer.Exit(1) from None


async def _run_planner(
    objective: str,
    files: list[str],
    out: Path,
    model: str,
    verbose: bool = False,  # noqa: FBT001, FBT002
) -> list[AgentDirective]:
    """Async helper to run the planner and save the output."""
    from jitsu.core.planner import JitsuPlanner  # noqa: PLC0415

    directives = None
    planner = None

    def on_progress(msg: str) -> None:
        typer.secho(f"  {msg}", fg=typer.colors.WHITE, dim=True, err=True)

    try:
        planner = JitsuPlanner(objective=objective, relevant_files=files)

        try:
            directives = await planner.generate_plan(
                model=model, on_progress=on_progress, verbose=verbose
            )
        except openai.APIStatusError as e:
            # 403 = OpenRouter Monthly Limit, 429 = Rate Limit
            if e.status_code in (403, 429):
                backup_model = "openai/gpt-oss-120b:free"
                typer.secho(
                    f"\n⚠️ API limit hit for {model}. Falling back to {backup_model}...",
                    fg=typer.colors.YELLOW,
                    bold=True,
                    err=True,
                )
                directives = await planner.generate_plan(
                    model=backup_model, on_progress=on_progress, verbose=verbose
                )
            else:
                raise

    except Exception as e:  # noqa: BLE001
        _handle_planner_error(e, verbose=verbose)

    if not directives or not planner:
        typer.secho(
            "❌ Planner failed to generate valid directives.", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(1)

    planner.save_plan(out)
    return directives


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
        Path, typer.Option("--out", "-o", help="Output path for the generated epic JSON.")
    ] = Path("epic.json"),
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help="The LLM model to use via OpenRouter.",
        ),
    ] = "openai/gpt-oss-120b:free",
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

    with typer.progressbar(length=100, label="Pondering...") as progress:
        # We run the planner. (Note: progress bar is just visual UX here since LLM calls are opaque in duration)
        anyio.run(_run_planner, objective, file_strings, out, model, verbose)
        progress.update(100)

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
    ] = "openai/gpt-oss-120b:free",
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose debug output.")
    ] = False,
) -> None:
    """Generate a Jitsu plan and immediately submit it to the server."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    epics_dir = Path.cwd() / "epics" / "current"
    epics_dir.mkdir(parents=True, exist_ok=True)
    out = epics_dir / f"epic_{timestamp}.json"

    file_strings = [str(f) for f in files] if files else []

    typer.secho(
        "🚀 Starting automated Jitsu pipeline...", fg=typer.colors.MAGENTA, bold=True, err=True
    )
    typer.secho(f"🧠 Step 1: Generating plan for: '{objective}'", fg=typer.colors.CYAN, err=True)

    with typer.progressbar(length=100, label="Pondering...") as progress:
        anyio.run(_run_planner, objective, file_strings, out, model, verbose)
        progress.update(100)

    typer.secho(
        f"✅ Plan successfully generated and saved to {out.relative_to(Path.cwd())}",
        fg=typer.colors.GREEN,
        err=True,
    )

    typer.secho("📡 Step 2: Submitting plan to server...", fg=typer.colors.CYAN, err=True)
    storage = EpicStorage()
    try:
        payload = storage.read_bytes(out)
        response = anyio.run(_send_payload, payload)

        if response.startswith("ACK"):
            typer.secho(f"✅ {response}", fg=typer.colors.GREEN, bold=True, err=True)

            # Auto-archive the epic file
            dest = storage.archive(out)

            typer.secho(
                f"📂 Pipeline complete. Epic archived to {storage.completed_rel(dest)}",
                fg=typer.colors.CYAN,
                err=True,
            )
        else:
            typer.secho(f"❌ Server Error: {response}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

    except OSError as e:
        typer.secho(f"❌ Failed to read or move epic file: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from e


async def _execute_phases(
    directives: list[AgentDirective], compiler: ContextCompiler, executor: JitsuExecutor
) -> None:
    """Execute each phase directive in the list."""
    for i, directive in enumerate(directives):
        typer.secho(
            f"\n▶️ Phase {i + 1}/{len(directives)}: {directive.phase_id}",
            fg=typer.colors.BLUE,
            bold=True,
            err=True,
        )

        with typer.progressbar(length=100, label="Compiling Context...") as progress:
            prompt = await compiler.compile_directive(directive)
            progress.update(100)

        with typer.progressbar(length=100, label="Executing...") as progress:
            success = executor.execute_directive(directive, prompt)
            progress.update(100)

        if not success:
            typer.secho(
                f"❌ Phase {directive.phase_id} failed to execute or verify. Stopping.",
                fg=typer.colors.RED,
                bold=True,
                err=True,
            )
            raise typer.Exit(1)

        typer.secho(f"✅ Phase {directive.phase_id} completed.", fg=typer.colors.GREEN, err=True)

        # 3. Commit Loop
        typer.secho("💾 Committing changes...", fg=typer.colors.CYAN, err=True)
        commit_msg = f"jitsu(auto): {directive.phase_id} - {directive.instructions[:50]}..."

        just_path = shutil.which("just")
        if not just_path:
            typer.secho("❌ 'just' executable not found in PATH.", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

        # Use anyio.run_process to avoid ASYNC221
        res = await anyio.run_process([just_path, "commit", commit_msg], check=False)
        if res.returncode != 0:
            typer.secho(
                f"⚠️ Commit failed: {res.stderr.decode('utf-8', errors='replace')}",
                fg=typer.colors.YELLOW,
                err=True,
            )
            raise typer.Exit(1)


async def _finalize_epic(out: Path, storage: EpicStorage | None = None) -> None:
    """Archive the epic file to the completed directory."""
    _storage = storage or EpicStorage()
    dest = await run_sync(_storage.archive, out)

    typer.secho(
        f"\n✨ Autonomous execution complete! Epic archived to {_storage.completed_rel(dest)}/{out.name}",
        fg=typer.colors.GREEN,
        bold=True,
        err=True,
    )


async def _run_autonomous_loop(directives: list[AgentDirective], out: Path) -> None:
    """Run the execution and commit loop for autonomous mode."""
    compiler = ContextCompiler()
    executor = JitsuExecutor()

    typer.secho(
        f"🏃 Step 2: Executing {len(directives)} phase(s) autonomously...",
        fg=typer.colors.CYAN,
        err=True,
    )

    await _execute_phases(directives, compiler, executor)
    await _finalize_epic(out)


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
    ] = "openai/gpt-oss-120b:free",
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

    directives: list[AgentDirective]
    out: Path

    typer.secho(
        "🤖 Starting Autonomous Jitsu Execution...", fg=typer.colors.MAGENTA, bold=True, err=True
    )

    if file:
        typer.secho(
            f"📦 Loading existing Epic plan from {file.name}...",
            fg=typer.colors.CYAN,
            err=True,
        )
        storage = EpicStorage()
        try:
            content = storage.read_text(file)
            adapter = TypeAdapter(list[AgentDirective])
            directives = adapter.validate_json(content)
            out = file
        except ValidationError as e:
            typer.secho(
                f"\n❌ Validation Error parsing {file.name}:\n{e}",
                fg=typer.colors.RED,
                bold=True,
                err=True,
            )
            raise typer.Exit(1) from e
        except OSError as e:
            typer.secho(
                f"\n❌ Failed to read {file.name}: {e}",
                fg=typer.colors.RED,
                bold=True,
                err=True,
            )
            raise typer.Exit(1) from e
    else:
        # objective is guaranteed to be set if file is not
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        epics_dir = Path.cwd() / "epics" / "current"
        epics_dir.mkdir(parents=True, exist_ok=True)
        out = epics_dir / f"epic_{timestamp}.json"

        file_strings = [str(f) for f in context] if context else []

        # 1. Plan
        typer.secho(
            f"🧠 Step 1: Generating plan for: '{objective}'", fg=typer.colors.CYAN, err=True
        )
        objective = cast("str", objective)
        directives = anyio.run(_run_planner, objective, file_strings, out, model, verbose)

    # 2. Execution Loop
    anyio.run(_run_autonomous_loop, directives, out)


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
