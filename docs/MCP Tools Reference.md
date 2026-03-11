# Jitsu MCP Tools Reference

Jitsu exposes a suite of tools via the Model Context Protocol (MCP) to allow IDE agents (Antigravity, Cursor, Windsurf) to self-orchestrate and pull context dynamically.

## 1. Orchestration & Queue Management

### `jitsu_get_next_phase`

- **Description**: Pulls the next `AgentDirective` from the server's internal queue. This is the primary entry point for agent execution. It automatically compiles the required context using the AST-first fallback compiler.
- **Usage**: Call this *first* when starting a new session or after reporting a successful phase.

### `jitsu_report_status`

- **Description**: Reports the completion status of the current phase back to the Jitsu state manager.
- **Parameters**:
  - `phase_id` (string): The ID of the phase being reported.
  - `status` (enum): `SUCCESS`, `FAILED`, `STUCK`.
  - `artifacts_generated` (array, optional): Files created or modified.
  - `agent_notes` (string, optional): Context for the next phase or human review.
  - `verification_output` (string, optional): Output from `just verify`.

### `jitsu_inspect_queue`

- **Description**: Returns a simplified list of all pending phases currently in the state manager.
- **Usage**: Useful for an agent to understand its remaining workload.

## 2. Dynamic Context & Progressive Disclosure

### `jitsu_request_context`

- **Description**: Allows an agent to request additional context "Just-In-Time" if the initial phase directive didn't include enough information.
- **Parameters**:
  - `target_identifier` (string): The symbol, file, or tree path.
  - `provider_name` (string): Options include `file`, `pydantic`, `ast`, `tree`, `env_var`, `git`, `markdown_ast`. Defaults to `file`.

### `jitsu_get_planning_context`

- **Description**: Bootstraps the agent for self-orchestration by providing a broad repository skeleton (`DirectoryTreeProvider`) and the contents of `.jitsurules`.
- **Usage**: Call this before generating an epic implementation plan.

## 3. Self-Orchestration

### `jitsu_submit_epic`

- **Description**: Allows an agent to dynamically submit an array of `AgentDirective` JSON objects directly into the server's queue.
- **Usage**: Used to spawn sub-tasks or implement an epic without dropping back to the CLI.

## 4. Git Lifecycle Management

### `jitsu_git_status`

- **Description**: Runs `git status --short` and returns the output to help the agent understand untracked and modified files.

### `jitsu_git_commit`

- **Description**: Commits all active changes using a strict format.
- **Parameters**:
  - `message` (string): A Conventional Commit message (e.g., `feat: added routing`).
  - `sync` (boolean): If true, runs `git push` after committing.
- **Note**: This delegates to the repository's `just commit` and `just sync` recipes to ensure security and pre-commit hooks are respected.
