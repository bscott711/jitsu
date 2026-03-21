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

    # The multi-phase stress test prompt
    prompt = (
        "We need to aggressively expand Jitsu's diagnostic capabilities by adding TWO new MCP tools. "
        "1. `jitsu_check_coverage`: Takes a test file path and module scope, runs pytest with coverage, and returns missing line numbers. "
        "2. `jitsu_run_linter`: Takes a target directory, runs 'uv run ruff check', and returns the parsed error output. "
        "Both tools must be fully implemented in handlers.py, registered in registry.py, and rigorously tested in test_handlers.py."
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
    options = PlannerOptions(
        verbose=True, 
        on_progress=on_progress
    )

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