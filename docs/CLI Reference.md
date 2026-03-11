# Jitsu CLI Reference

Jitsu provides a powerful CLI built on top of `typer` to manage the orchestration server and queue.

## `jitsu serve`

**Description:**
Starts the Jitsu ecosystem. This command boots up the MCP `stdio` server (for the IDE to connect to) and simultaneously spawns a background TCP daemon (IPC Server) listening on port `8765`.

- **Usage**: `uv run jitsu serve` (Usually configured directly in the IDE's MCP settings).

## `jitsu submit`

**Description:**
Submits a JSON Epic file to the running `jitsu serve` IPC daemon. This allows you to queue up work without interrupting the agent's active session.

- **Usage**: `uv run jitsu submit path/to/epic.json`

## `jitsu init`

**Description:**
Scaffolds a new project for Jitsu orchestration. This copies the default `.jitsurules` and `JustFile` from the `jitsu.templates` package into the current working directory.

- **Usage**: `uv run jitsu init`

## `jitsu queue ls`

**Description:**
Queries the background IPC daemon to print the current list of pending phases in the orchestrator's queue.

- **Usage**: `uv run jitsu queue ls`

## `jitsu queue clear`

**Description:**
Sends a command to the IPC daemon to immediately empty the execution queue.

- **Usage**: `uv run jitsu queue clear`

## `jitsu plan`

**Description:**
Uses an LLM (via OpenRouter/Instructor) to perform a Two-Pass (MapReduce) generation of an Epic based on a natural language prompt. It first determines the massive macro-architecture, then microscopic phases, and saves the result to `epic.json`.

- **Usage**: `uv run jitsu plan "Refactor the core logic to use X"`
- **Flags**: `--verbose` (dumps the JSON to stderr).

## `jitsu run`

**Description:**
Autonomous execution loop. Continuously pulls phases from the internal state, executes them via an LLM agent, runs verification (`just verify`), and reports status.

- **Usage**: `uv run jitsu run path/to/epic.json`
- **Flags**: `--auto-approve` (bypasses manual prompts for file edits), `--verbose`.

## `jitsu auto`

**Description:**
The ultimate autonomous command. Chains `plan` and `run` together. It generates an epic from a prompt and immediately begins executing it.

- **Usage**: `uv run jitsu auto "Fix the failing tests in module Y"`
