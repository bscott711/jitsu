# Server Module Architectural Audit Report

## 1. Tight System Coupling (Hardcoded Binary Paths)

**Nature of Violation:** In `src/jitsu/server/mcp_server.py` within `_handle_git_commit` (Line 324), the command executor hardcodes the path to the `just` binary:

```python
subprocess.run(["/opt/homebrew/bin/just", recipe, message], ...)
```

- **Impact:** This tightly couples the MCP server to MacOS environments using Homebrew. Any user running Linux, Windows, or even a different package manager on Mac will experience a hard crash. This violates the Dependency Inversion Principle.
- **Fix:** Use `shutil.which("just")` to dynamically resolve the binary path, similar to how it is properly handled in `cli/main.py`.

## 2. Open/Closed Principle Violation (Provider Hardcoding)

**Nature of Violation:** In `src/jitsu/server/mcp_server.py` within `_handle_request_context` (Line 231), the mapping of provider names to their classes is hardcoded:

```python
providers = {
    "file": FileStateProvider,
    "pydantic": PydanticProvider,
    # ...
}
```

- **Impact:** This is the exact same violation found in `core/compiler.py`. The JIT context handlers in the server have to be manually updated every time a new provider is added.
- **Fix:** The MCP server should retrieve the available providers from a centralized `ProviderRegistry` exported by the `providers` module.

## 3. Blind Exception Catching

**Nature of Violation:**

- `src/jitsu/server/mcp_server.py` (Line 289): `# noqa: BLE001` is used to swallow all exceptions natively during `_handle_submit_epic`.
- `src/jitsu/server/ipc.py` (Line 66): `except Exception as e:` handles unexpected errors but doesn't re-raise or terminate, which could hide deeper connection issues.
- **Impact:** Sweeping exceptions under the rug makes debugging network, validation, or OS-level failures opaque.
- **Fix:** Specifically catch expected exceptions (like `ValidationError` or `ConnectionError`) and properly log or return detailed `mcp.types.TextContent` errors.

## Recommended Structural Fixes

1. **Remove Hardcoded Paths:** Change `/opt/homebrew/bin/just` to dynamic path resolution.
2. **Centralize Provider Registry:** Eliminate the hardcoded `providers` dict and import a unified registry from `jitsu.providers`.
3. **Strict Error Handling:** Clean up `# noqa: BLE001` markers and catch specific expected exceptions.
