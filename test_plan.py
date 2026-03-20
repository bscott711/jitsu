"""Test script for verifying Jitsu Planner latency and output."""

import asyncio
import json
import logging
import os
import time
import traceback

import typer
from dotenv import load_dotenv

from jitsu.core.planner import JitsuPlanner

# Turn on raw HTTP network logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.DEBUG)


async def main() -> None:
    """Run a manual planning cycle to test model latency."""
    load_dotenv()

    prompt = (
        "Add a new MCP tool to Jitsu called jitsu_check_coverage. This tool should take a test file "
        "path and a target module scope, run a scoped pytest with coverage, and parse the output to "
        "return ONLY the missing line numbers."
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

    typer.echo("🧠 Sending prompt to OpenRouter/Nvidia (Now with Async Parallelism)...")

    start_time = time.perf_counter()

    try:
        # generate_plan returns a list[AgentDirective]
        plan = await planner.generate_plan()
        end_time = time.perf_counter()

        typer.echo(f"\n⏱️  LLM Generation Latency: {end_time - start_time:.2f} seconds")
        typer.echo(f"✅ Epic Plan Generated with {len(plan)} phases!")

        # Display the first phase as a sample
        if plan:
            typer.echo("Sample Phase Output:")
            typer.echo(json.dumps([directive.model_dump() for directive in plan], indent=2))

    except Exception:
        typer.secho("\n❌ CRITICAL PLANNER FAILURE ❌", fg=typer.colors.RED, bold=True)
        typer.echo("=" * 50)
        traceback.print_exc()
        typer.echo("=" * 50)
        raise


if __name__ == "__main__":
    asyncio.run(main())
