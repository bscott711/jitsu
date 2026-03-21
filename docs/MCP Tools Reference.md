# Jitsu MCP Tools Reference

Jitsu exposes a suite of **13 core tools** via the Model Context Protocol (MCP) to allow IDE agents to self-orchestrate and pull context dynamically.

## 1. Orchestration & Queue Management

### `jitsu_get_next_phase`

- **Description**: Pulls the next `AgentDirective` from the server's internal queue. This is the primary entry point for agent execution. It automatically compiles the required context using the AST-first **ContextCompiler**.
- **Usage**: Call this *first* when starting a new session or after reporting a successful phase.

### `jitsu_report_status`

- **Description**: Reports the completion status of the current phase back to the Jitsu state manager.
- **Parameters**:
  - `phase_id` (string): The ID of the phase being reported.
  - `status` (enum): `SUCCESS`, `FAILED`, `STUCK`.
  - `artifacts_generated` (array, optional): Files created or modified.
  - `agent_notes` (string, optional): Context for the next phase or human review.
  - `verification_output` (string, optional): Output from the verification step (e.g., `just verify`).

### `jitsu_inspect_queue`

- **Description**: Returns a simplified list of all pending phases currently in the state manager's queue.

## 2. Dynamic Context & Progressive Disclosure

### `jitsu_request_context`

- **Description**: Allows an agent to request additional context "Just-In-Time" if the initial phase directive didn't include enough information.
- **Parameters**:
  - `target_identifier` (string): The symbol, file, or tree path.
  - `provider_name` (string): Options include `file`, `pydantic`, `ast`, `tree`, `env_var`, `git`. Defaults to `file`.

### `jitsu_get_planning_context`

- **Description**: Bootstraps the agent for self-orchestration by providing a broad repository skeleton (`DirectoryTreeProvider`) and the contents of `.jitsurules`.
- **Usage**: Call this before generating an epic implementation plan.

## 3. Planning & Submission

### `jitsu_plan_epic`

- **Description**: A multi-pass planning tool that transforms a high-level natural language prompt into a structured, validated `Epic` (a list of `AgentDirectives`).
- **Parameters**:
  - `prompt` (string): The user's objective (e.g., "Refactor the auth module").
  - `relevant_files` (array, optional): A list of files to specifically analyze during planning.

### `jitsu_submit_epic`

- **Description**: Allows an agent to submit an array of `AgentDirective` objects directly into the server's queue.
- **Usage**: Used to load a generated plan into the orchestrator's state.

## 4. Git Lifecycle Management

### `jitsu_git_status`

- **Description**: Runs `git status --short` and returns the output to help the agent understand untracked and modified files.

### `jitsu_git_commit`

- **Description**: Commits all active changes and optionally syncs them.
- **Parameters**:
  - `message` (string): A Conventional Commit message (e.g., `feat: added routing`).
  - `sync` (boolean): If true, runs `git push` after committing.

## 5. Testing & Validation

### `jitsu_check_coverage`

- **Description**: Runs a scoped `pytest` coverage check on a specific test file and set of source modules. Returns a JSON mapping of missing line numbers per file.
- **Parameters**:
  - `test_file_path` (string): The path to the test file to execute.
  - `module_scope` (array): A list of module strings to track (e.g., `["jitsu.core", "jitsu.providers"]`).

## 6. AST-Based Code Modification

### `jitsu_ast_rename_function`

- **Description**: Renames a function or method in a Python file using AST transformation.
- **Parameters**:
  - `file_path` (string): Path to the target Python file.
  - `old_name` (string): Current name of the function or method to rename.
  - `new_name` (string): New name to assign to the function or method.

### `jitsu_ast_rename_class`

- **Description**: Renames a class in a Python file using AST transformation.
- **Parameters**:
  - `file_path` (string): Path to the target Python file.
  - `old_name` (string): Current name of the class to rename.
  - `new_name` (string): New name to assign to the class.

### `jitsu_ast_add_parameter`

- **Description**: Adds a parameter to a function's signature in a Python file using AST transformation.
- **Parameters**:
  - `file_path` (string): Path to the target Python file.
  - `func_name` (string): Name of the function to modify.
  - `param_name` (string): Name of the parameter to add.
  - `default_value` (string, optional): String representation of the default value for the new parameter (e.g., `"None"`, `"'default'"`).
