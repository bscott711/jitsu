"""Test script for verifying Jitsu Planner latency and output."""

import asyncio
import logging
import os
import time
import traceback

import typer
from dotenv import load_dotenv

from jitsu.core.planner import JitsuPlanner
from jitsu.models.execution import PlannerOptions

# Turn off httpx debug logging so it doesn't drown out our progress UI
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def main() -> None:
    """Run a manual planning cycle to test model latency and progress streaming."""
    load_dotenv()

    # The Observability Epic stress test prompt
    prompt = (
        "Implement dynamic observability for the Jitsu Planner to expose LLM generation and Pydantic validation errors without restarting the server.\n\n"
        "Phase 1: Update the `jitsu_plan_epic` tool schema in `src/jitsu/server/registry.py` and `src/jitsu/server/handlers.py` to accept an optional `verbose: bool = False` parameter.\n"
        "Phase 2: Inside the `jitsu_plan_epic` handler, if `verbose` is true, create a `PlannerOptions(verbose=True)` object. CRITICAL: Define an `on_progress` async callback that writes strictly to `sys.stderr` (e.g., `sys.stderr.write(msg + '\\n')` and `sys.stderr.flush()`) so it does not corrupt the MCP stdout JSON-RPC stream. Pass these options to `planner.generate_plan(options=options)`.\n"
        "Phase 3: Update `src/jitsu/core/planner.py` to ensure that when a Pydantic `ValidationError` or generic Exception occurs during the retry loop, the full traceback is printed to `sys.stderr` if `verbose` is True.\n\n"
        "CRITICAL CONSTRAINT: Use strictly scoped `verification_commands` (e.g., `uv run ruff check src/jitsu/server/handlers.py` and `uv run pytest tests/server -n auto`). Do NOT use empty arrays or 'just verify'."
    )

    planner = JitsuPlanner(
        objective=prompt,
        relevant_files=[
            "src/jitsu/server/handlers.py",
            "src/jitsu/server/registry.py",
            "src/jitsu/core/planner.py",
        ],
    )

    typer.echo("🚀 Booting Jitsu Planner...")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        typer.secho("❌ Error: OPENROUTER_API_KEY not found in .env", fg=typer.colors.RED)
        return

    planner = JitsuPlanner(
        objective=prompt,
        relevant_files=[
            "src/jitsu/server/handlers.py",
            "src/jitsu/server/registry.py",
            "tests/server/test_handlers.py",
        ],
    )

    typer.echo("🧠 Sending prompt to OpenRouter/Nvidia (Parallel Execution)...")

    # 1. Create a progress callback to stream status updates in real-time
    async def on_progress(msg: str) -> None:
        typer.secho(f"  ⏳ {msg}", fg=typer.colors.CYAN)

    # 2. Set verbose=True to print the blueprint mid-flight
    options = PlannerOptions(verbose=True, on_progress=on_progress)

    start_time = time.perf_counter()

    try:
        # Pass the options into the planner
        plan = await planner.generate_plan(options=options)
        end_time = time.perf_counter()

        typer.echo(f"\n⏱️  LLM Generation Latency: {end_time - start_time:.2f} seconds")
        typer.echo(f"✅ Epic Plan Generated with {len(plan)} phases!")

        if plan:
            typer.echo("\nSample Final Output (Phase 1):")
            typer.echo(plan[0].model_dump_json(indent=2))  # Single item has .model_dump_json()

    except Exception:
        typer.secho("\n❌ CRITICAL PLANNER FAILURE ❌", fg=typer.colors.RED, bold=True)
        typer.echo("=" * 50)
        traceback.print_exc()
        typer.echo("=" * 50)
        raise


if __name__ == "__main__":
    asyncio.run(main())
