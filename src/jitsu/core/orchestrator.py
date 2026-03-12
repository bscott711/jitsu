"""JitsuOrchestrator: Autonomous planning and execution loop."""

import shutil
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import anyio
import openai
import typer
from anyio.to_thread import run_sync
from instructor.core.exceptions import InstructorRetryException
from pydantic import TypeAdapter, ValidationError

from jitsu.core.compiler import ContextCompiler
from jitsu.core.executor import JitsuExecutor, MonotonicityError
from jitsu.core.planner import JitsuPlanner
from jitsu.core.state import JitsuStateManager
from jitsu.core.storage import EpicStorage
from jitsu.models.core import AgentDirective, PhaseReport, PhaseStatus
from jitsu.providers.git import GitError, GitProvider


class JitsuOrchestrator:
    """
    Encapsulates planning, execution, and archiving for autonomous Jitsu runs.

    All orchestration logic that was previously scattered across private helper
    functions in ``cli/main.py`` lives here.  The CLI commands become thin
    wrappers that instantiate this class and delegate to its public methods.

    Args:
        planner: Optional ``JitsuPlanner`` instance for dependency injection.
        executor: Optional ``JitsuExecutor`` instance for dependency injection.
        storage: Optional ``EpicStorage`` instance.  Defaults to ``EpicStorage()``.

    """

    def __init__(
        self,
        planner: JitsuPlanner | None = None,
        executor: JitsuExecutor | None = None,
        storage: EpicStorage | None = None,
        on_progress: Callable[[str], None] | None = None,
        state_manager: JitsuStateManager | None = None,
    ) -> None:
        """Initialise the orchestrator with optional DI'd collaborators."""
        self.planner = planner
        self.executor = executor or JitsuExecutor()
        self.storage = storage or EpicStorage()
        self.state_manager = state_manager or JitsuStateManager()
        self.on_progress = on_progress
        self._original_branch: str | None = None
        self._sandbox_branch: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_plan(
        self,
        objective: str,
        files: list[str],
        out: Path,
        *,
        model: str,
        verbose: bool = False,
    ) -> list[AgentDirective]:
        """
        Run the planner and save the epic JSON to *out*.

        The ``verbose`` and ``model`` parameters are keyword-only to avoid the
        boolean-trap anti-pattern.  Progress callbacks are supplied via
        ``on_progress`` in ``__init__``.

        Args:
            objective: Natural-language goal.
            files: Relevant file paths (as strings) for context.
            out: File path where the resulting epic JSON will be written.
            model: LLM model identifier.
            verbose: Emit extra debug output when ``True``.

        Returns:
            List of generated ``AgentDirective`` objects.

        Raises:
            typer.Exit: On any planning failure.

        """
        planner = self.planner or JitsuPlanner(objective=objective, relevant_files=files)

        directives: list[AgentDirective] | None = None

        def _progress(msg: str) -> None:
            if self.on_progress:
                self.on_progress(msg)

        try:
            try:
                directives = await planner.generate_plan(
                    model=model, on_progress=_progress, verbose=verbose
                )
            except openai.APIStatusError as e:
                # 403 = OpenRouter monthly limit, 429 = rate limit
                if e.status_code in (403, 429) and model != "openai/gpt-oss-120b:free":
                    backup_model = "openai/gpt-oss-120b:free"
                    typer.secho(
                        f"\n⚠️ API limit hit for {model}. Falling back to {backup_model}...",
                        fg=typer.colors.YELLOW,
                        bold=True,
                        err=True,
                    )
                    directives = await planner.generate_plan(
                        model=backup_model, on_progress=_progress, verbose=verbose
                    )
                else:
                    raise

        except (RuntimeError, openai.APIStatusError, InstructorRetryException) as e:
            self.handle_planner_error(e, verbose=verbose)

        if not directives:
            typer.secho(
                "❌ Planner failed to generate valid directives.", fg=typer.colors.RED, err=True
            )
            raise typer.Exit(1)

        planner.save_plan(out)
        return directives

    async def execute_plan(
        self,
        objective: str,
        files: list[str],
        out: Path,
        *,
        model: str,
        verbose: bool = False,
    ) -> list[AgentDirective]:
        """
        Execute the planning phase with a progress bar.

        Args:
            objective: Natural-language goal.
            files: Relevant file paths (as strings) for context.
            out: File path where the resulting epic JSON will be written.
            model: LLM model identifier.
            verbose: Emit extra debug output when ``True``.

        Returns:
            List of generated ``AgentDirective`` objects.

        """
        with typer.progressbar(length=100, label="Pondering...") as progress:
            directives = await self.run_plan(objective, files, out, model=model, verbose=verbose)
            progress.update(100)
        return directives

    async def execute_run(
        self,
        objective: str,
        files: list[str],
        *,
        model: str,
        verbose: bool = False,
    ) -> None:
        """
        Generate a plan and immediately submit it to the server.

        Args:
            objective: Natural-language goal.
            files: Relevant file paths (as strings) for context.
            model: LLM model identifier.
            verbose: Emit extra debug output when ``True``.

        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = self.storage.current_dir / f"epic_{timestamp}.json"

        typer.secho(
            f"🧠 Step 1: Generating plan for: '{objective}'", fg=typer.colors.CYAN, err=True
        )

        await self.execute_plan(objective, files, out, model=model, verbose=verbose)

        typer.secho(
            f"✅ Plan successfully generated and saved to {self.storage.rel_path(out)}",
            fg=typer.colors.GREEN,
            err=True,
        )

        typer.secho("📡 Step 2: Submitting plan to server...", fg=typer.colors.CYAN, err=True)
        try:
            payload = self.storage.read_bytes(out)
            response = await self.send_payload(payload)

            if response.startswith("ACK"):
                typer.secho(f"✅ {response}", fg=typer.colors.GREEN, bold=True, err=True)
                dest = await run_sync(self.storage.archive, out)
                typer.secho(
                    f"📂 Pipeline complete. Epic archived to {self.storage.completed_rel(dest)}",
                    fg=typer.colors.CYAN,
                    err=True,
                )
            else:
                typer.secho(f"❌ Server Error: {response}", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)

        except OSError as e:
            typer.secho(f"❌ Failed to read or move epic file: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1) from e

    async def execute_auto(
        self,
        objective: str | None = None,
        file: Path | None = None,
        context: list[Path] | None = None,
        *,
        model: str,
        verbose: bool = False,
    ) -> None:
        """
        Execute an epic autonomously, either from an objective or an existing file.

        Args:
            objective: Natural-language goal (optional if *file* is provided).
            file: Path to an existing epic JSON (optional if *objective* is provided).
            context: Relevant files to provide as context.
            model: LLM model identifier.
            verbose: Emit extra debug output when ``True``.

        """
        directives: list[AgentDirective]
        out: Path

        if file:
            typer.secho(
                f"📦 Loading existing Epic plan from {file.name}...",
                fg=typer.colors.CYAN,
                err=True,
            )
            try:
                content = await run_sync(self.storage.read_text, file)
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
            if not objective:
                # This should be caught by Typer, but we guard here too
                typer.secho(
                    "❌ Objective required if file is not provided",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(1)

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            out = self.storage.current_dir / f"epic_{timestamp}.json"

            file_strings = [str(f) for f in context] if context else []
            typer.secho(
                f"🧠 Step 1: Generating plan for: '{objective}'", fg=typer.colors.CYAN, err=True
            )
            directives = await self.execute_plan(
                objective, file_strings, out, model=model, verbose=verbose
            )

        await self.run_autonomous(directives, out)

    async def send_payload(self, payload: bytes, port: int = 8765) -> str:
        """Async helper to send the payload over TCP and await response."""
        try:
            async with await anyio.connect_tcp("127.0.0.1", port) as client:
                await client.send(payload)
                await client.send_eof()

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

    async def execute_phases(
        self,
        directives: list[AgentDirective],
        compiler: ContextCompiler | None = None,
        out: Path | None = None,
    ) -> None:
        """
        Execute each directive in sequence, verifying and committing after each.

        Args:
            directives: The ordered list of phases to execute.
            compiler: Optional ``ContextCompiler`` instance.
            out: Optional Path to the epic file for state persistence.

        Raises:
            typer.Exit: If any phase fails or the commit step fails.

        """
        _compiler = compiler or ContextCompiler()

        for i, directive in enumerate(directives):
            typer.secho(
                f"\n▶️ Phase {i + 1}/{len(directives)}: {directive.phase_id}",
                fg=typer.colors.BLUE,
                bold=True,
                err=True,
            )

            with typer.progressbar(length=100, label="Compiling Context...") as progress:
                prompt = await _compiler.compile_directive(directive)
                progress.update(100)

            try:
                with typer.progressbar(length=100, label="Executing...") as progress:
                    success = await self.executor.execute_directive(directive, prompt)
                    progress.update(100)
            except MonotonicityError as e:
                report = PhaseReport(
                    phase_id=directive.phase_id,
                    status=PhaseStatus.STUCK,
                    agent_notes=str(e),
                )
                self.state_manager.update_phase(report)
                if out:
                    out.with_suffix(".state").write_text(report.model_dump_json())

                typer.secho(
                    f"\n❌ Phase {directive.phase_id} is STUCK: {e}",
                    fg=typer.colors.RED,
                    bold=True,
                    err=True,
                )
                await self._handle_quarantine()
                raise typer.Exit(1) from e

            if not success:
                report = PhaseReport(
                    phase_id=directive.phase_id,
                    status=PhaseStatus.FAILED,
                    agent_notes="Max retries reached or verification failed.",
                )
                self.state_manager.update_phase(report)
                if out:
                    out.with_suffix(".state").write_text(report.model_dump_json())

                typer.secho(
                    f"❌ Phase {directive.phase_id} failed to execute or verify. Stopping.",
                    fg=typer.colors.RED,
                    bold=True,
                    err=True,
                )
                await self._handle_quarantine()
                raise typer.Exit(1)

            typer.secho(
                f"✅ Phase {directive.phase_id} completed.", fg=typer.colors.GREEN, err=True
            )

            # Commit after each successful phase
            typer.secho("💾 Committing changes...", fg=typer.colors.CYAN, err=True)
            commit_msg = f"jitsu(auto): {directive.phase_id} - {directive.instructions[:50]}..."

            just_path = shutil.which("just")
            if not just_path:
                typer.secho(
                    "❌ 'just' executable not found in PATH.", fg=typer.colors.RED, err=True
                )
                raise typer.Exit(1)

            res = await anyio.run_process([just_path, "commit", commit_msg], check=False)
            if res.returncode != 0:
                typer.secho(
                    f"⚠️ Commit failed: {res.stderr.decode('utf-8', errors='replace')}",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                raise typer.Exit(1)

    async def finish(self, out: Path) -> None:
        """
        Archive the epic file and cleanup sandbox branch.

        Args:
            out: The epic JSON file to archive.

        """
        if self._original_branch and self._sandbox_branch:
            git = GitProvider(self.executor.workspace_root)
            git.merge_branch(self._sandbox_branch, self._original_branch)
            git.delete_branch(self._sandbox_branch)

        dest = await run_sync(self.storage.archive, out)

        typer.secho(
            f"\n✨ Autonomous execution complete! Epic archived to {self.storage.completed_rel(dest)}",
            fg=typer.colors.GREEN,
            bold=True,
            err=True,
        )

    async def run_autonomous(self, directives: list[AgentDirective], out: Path) -> None:
        """
        Execute all phases then archive the epic.

        Args:
            directives: The phases to run.
            out: The epic JSON file to archive on completion.

        """
        if directives:
            git = GitProvider(self.executor.workspace_root)
            self._original_branch = git.get_current_branch()
            self._sandbox_branch = f"jitsu-run/{directives[0].epic_id}"

            typer.secho(
                f"🌿 Creating sandbox branch: {self._sandbox_branch}",
                fg=typer.colors.CYAN,
                err=True,
            )
            git.create_and_checkout_branch(self._sandbox_branch)

        typer.secho(
            f"🏃 Step 2: Executing {len(directives)} phase(s) autonomously...",
            fg=typer.colors.CYAN,
            err=True,
        )
        await self.execute_phases(directives, out=out)
        await self.finish(out)

    async def _handle_quarantine(self) -> None:
        """Commit WIP to sandbox and restore original branch."""
        if not self._original_branch or not self._sandbox_branch:
            return

        git = GitProvider(self.executor.workspace_root)
        try:
            # Commit WIP
            just_path = shutil.which("just")
            if just_path:
                await anyio.run_process(
                    [just_path, "commit", "chore(jitsu): HALTED - Max retries exhausted"],
                    check=False,
                )

            git.checkout_branch(self._original_branch)
            typer.secho(
                f"⚠️ Epic HALTED. Workspace restored to '{self._original_branch}'. WIP preserved in '{self._sandbox_branch}'.",
                fg=typer.colors.YELLOW,
                bold=True,
                err=True,
            )
        except (GitError, OSError) as e:
            typer.secho(f"⚠️ Quarantine failed: {e}", fg=typer.colors.RED, err=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def handle_planner_error(e: Exception, *, verbose: bool = False) -> None:
        """
        Translate planner exceptions into CLI error output and exit.

        Args:
            e: The exception to handle.
            verbose: Emit debug details when ``True``.

        """
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
