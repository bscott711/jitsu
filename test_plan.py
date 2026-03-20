import asyncio
import logging
import os
import time
import traceback

from dotenv import load_dotenv

from jitsu.core.planner import JitsuPlanner

# --- NEW: Turn on raw HTTP network logging ---
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.DEBUG)
# ---------------------------------------------


async def main():
    # 1. Force load the environment variables
    load_dotenv()

    prompt = (
        "Add a new MCP tool to Jitsu called jitsu_check_coverage. This tool should take a test file "
        "path and a target module scope, run a scoped pytest with coverage, and parse the output to "
        "return ONLY the missing line numbers so the agent can quickly patch coverage gaps without context bloat."
    )

    print("🚀 Booting Jitsu Planner...")

    # 2. Verify the API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    print(f"🔑 OPENROUTER_API_KEY detected: {'YES' if api_key else 'NO (Check your .env file!)'}")

    planner = JitsuPlanner(
        objective=prompt,
        relevant_files=[
            "src/jitsu/server/handlers.py",
            "src/jitsu/server/registry.py",
            "tests/server/test_handlers.py",
        ],
    )

    print("🧠 Sending prompt to OpenRouter/Nvidia...")

    # --- START TIMER ---
    start_time = time.perf_counter()

    try:
        plan = await planner.generate_plan()

        # --- END TIMER ---
        end_time = time.perf_counter()

        print(f"\n⏱️  LLM Generation Latency: {end_time - start_time:.2f} seconds")
        print("✅ Epic Plan Generated Successfully!")
        print(plan.model_dump_json(indent=2))

    except Exception:
        print("\n❌ CRITICAL PLANNER FAILURE ❌")
        print("=" * 50)
        traceback.print_exc()
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
