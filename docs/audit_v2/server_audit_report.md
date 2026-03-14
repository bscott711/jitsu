# V2 Audit Report: `src/jitsu/server`

> **Generated:** 2026-03-14 02:25:02 UTC

## 1. Dead Code Analysis (Vulture)

```text
src/jitsu/server/mcp_server.py:23: unused function 'handle_list_tools' (60% confidence)
src/jitsu/server/mcp_server.py:29: unused function 'handle_call_tool' (60% confidence)
```

## 2. Cognitive Complexity (Complexipy)

```text
──────────────────────────────────────── 🐙 complexipy ────────────────────────────────────────
server/handlers.py
    ToolHandlers::__init__ 0 PASSED
    ToolHandlers::handle_git_status 0 PASSED
    ToolHandlers::register_all 0 PASSED
    ToolHandlers::handle_get_next_phase 1 PASSED
    ToolHandlers::handle_inspect_queue 1 PASSED
    ToolHandlers::handle_get_planning_context 2 PASSED
    ToolHandlers::handle_request_context 3 PASSED
    ToolHandlers::handle_submit_epic 7 PASSED
    ToolHandlers::handle_report_status 8 PASSED
    ToolHandlers::handle_git_commit 9 PASSED
    ToolHandlers::handle_plan_epic 15 PASSED

server/mcp_server.py
    handle_call_tool 0 PASSED
    handle_list_tools 0 PASSED
    run_server 0 PASSED
    handle_agent_plan 2 PASSED

server/registry.py
    ToolRegistry::__init__ 0 PASSED
    ToolRegistry::get_tools 0 PASSED
    ToolRegistry::register 0 PASSED
    ToolRegistry::execute 7 PASSED

All functions are within the allowed complexity.
────────────────────────────────── 🎉 Analysis completed! 🎉 ──────────────────────────────────
```

## 3. Linting (Ruff)

```text
All checks passed!
```

## 4. Static Typing (Pyright)

```text
0 errors, 0 warnings, 0 informations
```

## 5. Technical Debt (Inline Ignores)

- **src/jitsu/server/handlers.py:181** ` await self.server.send_notification(  # type: ignore[reportAttributeAccessIssue] `

---

*End of automated report.*
