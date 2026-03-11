# CLI Module Architectural Audit Report

## 1. Separation of Concerns (SoC) Violations

**Nature of Violation:** `src/jitsu/cli/main.py` functions as both a UI layer (CLI argument parsing and formatting) and a core orchestration layer. It manages planning loops, autonomous execution loops, network requests (TCP via `anyio`), and direct Epic file disk I/O.

- **Orchestration Logic**: `_run_planner`, `_execute_phases`, and `_run_autonomous_loop` are defined directly in the CLI module. They handle complex async logic, fallback models for rate limits, and error handling for the LLM client.
- **Direct Disk I/O**: The commands `run`, `auto`, `submit`, and `serve` handle bare file paths and manipulate the Epic JSON lifecycle (e.g., `completed_dir.mkdir(...)`, `out.rename(...)`). This belongs in an `EpicManager` abstraction.
- **Network Logic**: `_send_payload` opens TCP connections directly.

## 2. Testing Constraints (Coupling)

**Nature of Violation:** Because the CLI module is tightly coupled to OS operations, process control, and async execution, the tests in `tests/cli/test_main.py` suffer from over-mocking.

- **Heavy Mocking**: Tests rely heavily on `patch("jitsu.cli.main.anyio.run")` passing injected side effects to simulate the orchestration flow without actually running it.
- **No Dependency Injection**: The CLI handlers instantiate `JitsuPlanner` and `JitsuExecutor` directly instead of receiving them, forcing tests to patch import locations globally.

## 3. DRY (Don't Repeat Yourself) Violations

**Nature of Violation:** Error handling for the LLM is duplicated.

- In `_run_planner`, it manually captures `openai.APIStatusError` to fallback to a different model. Similar API error capturing resides in other modules (`executor.py`).
- File opening logic (try/except `OSError`, `ValidationError`) is duplicated across `serve()`, `submit()`, and `auto()`.

## 4. Supressed Checks (`# noqa` and `# pragma`)

- **# noqa: BLE001 (Blind Exception Catching):** Used in `serve` (line 139) and `_run_planner` (line 373) to blindly catch `Exception`.
- **# noqa: FBT001, FBT002 (Boolean Traps):** Used in `_handle_planner_error` and `_run_planner` for the `verbose: bool` flag.
- **# noqa: PLC0415 (Import outside top level):** Used in `_run_planner` for lazy-loading `JitsuPlanner`.
- **# pragma: no cover:** Used at the `__main__` guard (line 701).

## Recommended Structural Fixes

1. **Extract Orchestrator**: Move `_run_planner`, `_run_autonomous_loop`, and `_execute_phases` to `src/jitsu/core/orchestrator.py`.
2. **Extract State/Storage Manager**: Create a class (e.g. `EpicStorage`) that handles the loading, archiving, and error-handling of `.json` epic files.
3. **Extract Network Client**: Move `_send_payload` to `src/jitsu/server/client.py`.
4. **Refactor Boolean Traps**: Change the `verbose` boolean argument in helper functions to an Enum or distinct functions, eliminating the `FBT` noqa tags.
5. **Fix Exception Handling**: Catch specific exceptions dynamically instead of `Exception`, eliminating `BLE001`.
