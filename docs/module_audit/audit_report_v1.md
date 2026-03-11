# Jitsu Architectural Audit Report v1

## 1. Hardcoded System Prompts

**Nature of Violation:** Hardcoding system prompts directly into logic classes prevents reusability, makes testing difficult, and violates the Separation of Concerns. Prompts should be externalized (e.g., in `docs/` or `src/jitsu/templates/`).

* **`src/jitsu/core/executor.py`**
  * **Lines 757-763:** `system_prompt` is hardcoded as a string directly inside `JitsuExecutor.execute_directive`.

* **`src/jitsu/core/planner.py`**
  * **Line 910:** Fallback system prompt `"You are a helpful assistant."` is hardcoded.
  * **Lines 934-940:** `blueprint_system_prompt` appends hardcoded rules for drafting the high-level blueprint.
  * **Lines 961-970:** `phase_system_prompt` appends hardcoded rules for generating specific phases.

*(Note: Although `cli/main.py` was mentioned in the prompt, it delegates planning to `core/planner.py`, where the hardcoded prompts actually reside.)*

## 2. Duplication of LLM Client Initialization and Environment Loading

**Nature of Violation:** Multiple files independently load the environment via `dotenv.load_dotenv()` and instantiate the `instructor` OpenAI client. This violates DRY and makes it hard to manage credentials or swap underlying LLM providers globally.

* **`src/jitsu/core/executor.py`**
  * **Lines 735-748:** Calls `dotenv.load_dotenv()`, checks for `OPENROUTER_API_KEY`, and initializes `instructor.from_openai()`.
* **`src/jitsu/core/planner.py`**
  * **Lines 884-898:** Identical logic calling `dotenv.load_dotenv()`, checking for `OPENROUTER_API_KEY`, and initializing `instructor.from_openai()`.

## 3. Separation of Concerns Violations in `cli/main.py`

**Nature of Violation:** `cli/main.py` is overloaded. It should primarily handle argument parsing and UI formatting (via `typer.secho`). Instead, it currently manages complex orchestration (planning loops) and direct file I/O for state management, which belongs in a dedicated orchestrator or state manager module.

* **Lines 334-384 (`_run_planner`):** Handles the instantiation of `JitsuPlanner`, manages OpenRouter API limits/fallbacks (`openai.APIStatusError`), and triggers saving the plan.
* **Lines 512-562 (`_execute_phases`):** Orchestrates the loop over directives, calling `ContextCompiler` and `JitsuExecutor`, and directly shelling out to `just commit`.
* **Lines 240-271 (`submit`), Lines 437-511 (`run`), Lines 563-576 (`_finalize_epic`):** Handles bare file I/O (e.g., `completed_dir.mkdir(...)`, `out.rename(...)`) for managing Epic lifecycle on disk.
* **Lines 64-147 (`serve`), Lines 593-694 (`auto`):** Loads Epic JSON files directly, processes `ValidationError`, and orchestrates the autonomous execution loop.

## 4. Remaining `# noqa` and `# pragma` Markers

**Nature of Violation:** These markers suppress linting and coverage checks, often masking underlying issues like blind exception catching, unused imports, or untested logic.

* **`# noqa: BLE001` (Blind Exception Catching):**
  * `src/jitsu/cli/main.py`: Lines 139, 373
  * `src/jitsu/providers/markdown.py`: Line 52
  * `src/jitsu/providers/tree.py`: Lines 61, 102
  * `src/jitsu/providers/file.py`: Line 27
  * `src/jitsu/server/mcp_server.py`: Line 289
* **`# noqa: FBT001, FBT002` (Boolean Traps):**
  * `src/jitsu/cli/main.py`: Lines 291, 339
* **`# noqa: PLC0415` (Import outside top level):**
  * `src/jitsu/cli/main.py`: Line 342
* **`# pragma: no cover`:**
  * `src/jitsu/cli/main.py`: Line 701 (`if __name__ == "__main__":`)

## Recommended Structural Fixes

1. **Prompt Management:** Extract all hardcoded strings into a `src/jitsu/prompts.py` module or template files (`.md` or `.j2`) similar to how CLI templates are handled.
2. **Client Factory:** Create a unified `LLMClientFactory` or `config.py` module that handles `dotenv` initialization and returns a configured `instructor` client. Inject this client into Planner and Executor.
3. **CLI Refactoring:** Extract execution and planning orchestration into a new `src/jitsu/core/orchestrator.py` module. Extract Epic file management (loading, saving, archiving) into an `EpicManager` wrapper class.
4. **Linting Cleanup:** Remove `# noqa: BLE001` by catching specific exceptions or adding logging. Refactor boolean flags in CLI handlers to use Enums or distinct methods to fix `# noqa: FBT...`. Add test coverage for the `__main__` entrypoint.
