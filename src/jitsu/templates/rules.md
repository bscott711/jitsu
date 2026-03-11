# **Jitsu Workflow Protocol**

You are operating under Jitsu (実) orchestration.

1. **Initialization:** At the start of every session or task, you MUST call the `jitsu_get_next_phase` tool.
2. **Strict Context:** Read the compiled Markdown context provided by Jitsu. This is your "Ground Truth." Do not rely on stale file states or previous conversation memory if it conflicts with the JIT context.
3. **Execution:** Execute the instructions within the specified `module_scope`.
4. **Git Lifecycle:** You MUST use `jitsu_git_status` to check your changes and `jitsu_git_commit` to stage and commit them. All commit messages MUST follow [Conventional Commits](https://www.conventionalcommits.org/).
5. **Self-Orchestration:** If you are tasked with planning an Epic, use `jitsu_get_planning_context` to gather repository intelligence and `jitsu_submit_epic` to queue the generated phases.
6. **Reporting:** Once the task is complete, you MUST call `jitsu_report_status` with your artifacts and notes.
7. **Errors:** If you encounter a validation error or become stuck, report the status as `STUCK` to trigger the meta-feedback loop.
8. **Protocol Safety (stdio):** Never use `print()` or standard `logging`. The MCP server communicates via JSON-RPC over stdout. Any rogue text on stdout will crash the protocol. All logs, exceptions, and CLI outputs MUST be explicitly routed to `sys.stderr`.
9. **Execution Environment:** You MUST ALWAYS use `just verify` for all repository-level execution, testing, and linting. Do not use system `python3`, global `pytest`, or manual `uv run` commands for full verification. Do not manually activate virtual environments or reference `./.venv/bin/python` directly.
