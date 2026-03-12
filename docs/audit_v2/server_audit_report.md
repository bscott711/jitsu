# V2 Audit Report: `src/jitsu/server`

>
> **Generated:** 2026-03-12 06:06:38 UTC

## 1. Dead Code Analysis (Vulture)

```text
src/jitsu/server/client.py:7: unused function 'send_payload' (60% confidence)
src/jitsu/server/mcp_server.py:22: unused function 'handle_list_tools' (60% confidence)
src/jitsu/server/mcp_server.py:28: unused function 'handle_call_tool' (60% confidence)
```

## 2. Cognitive Complexity (Complexipy)

```text
──────────────────────────────────────── 🐙 complexipy ────────────────────────────────────────
server/client.py
    send_payload 2 PASSED

server/handlers.py
    ToolHandlers::__init__ 0 PASSED
    ToolHandlers::handle_git_status 0 PASSED
    ToolHandlers::register_all 0 PASSED
    ToolHandlers::handle_get_next_phase 1 PASSED
    ToolHandlers::handle_inspect_queue 1 PASSED
    ToolHandlers::handle_get_planning_context 2 PASSED
    ToolHandlers::handle_request_context 3 PASSED
    ToolHandlers::handle_report_status 6 PASSED
    ToolHandlers::handle_submit_epic 7 PASSED
    ToolHandlers::handle_git_commit 9 PASSED

server/ipc.py
    IPCServer::__init__ 0 PASSED
    IPCServer::serve 0 PASSED
    IPCServer::_process_json_payload 1 PASSED
    IPCServer::_handle_command 5 PASSED
    IPCServer::handle_client 9 PASSED

server/mcp_server.py
    handle_call_tool 0 PASSED
    handle_list_tools 0 PASSED
    run_server 0 PASSED

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

- **src/jitsu/server/handlers.py:130** ` except Exception as e:  # noqa: BLE001 `

---

*End of automated report.*
