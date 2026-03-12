# **Layer 3: Transport & Orchestration**

Layer 3 is the interface between Jitsu and the outside world. It handles the Model Context Protocol (MCP) transport and the Command Line Interface (CLI).

---

## **Decoupled Architecture**

Jitsu follows a strict separation of concerns between its transport mechanism and its tool logic. This decoupling ensures that the system is testable, extensible, and robust.

### **`mcp_server.py`: The Transport Layer**

The `mcp_server.py` module acts strictly as a **transport mechanism**. It handles the MCP lifecycle (stdio/SSE), tool listing, and incoming call routing. Crucially, it **does not** contain business logic.

- **Role**: Listener and Dispatcher.
- **IPC Daemon**: Spawns a background listener for cross-process communication (via `jitsu submit`).
- **Delegation**: It delegates all tool execution to the `ToolHandlers` class.

### **`ToolHandlers`: The Execution Layer**

The `ToolHandlers` class encapsulates the actual logic for every Jitsu tool. It is "injected" with the necessary core components (`JitsuStateManager` and `ContextCompiler`).

- **Logic Capsulation**: All `handle_*` methods are contained here.
- **Statelessness**: The handlers operate on the state managed by Layer 1, making them easy to unit test without an active MCP connection.

### **`ToolRegistry`: The Router**

Routing is handled by a dedicated `ToolRegistry`. This registry maps tool names to their corresponding logic in `ToolHandlers`, further decoupling the server from the specific tool implementation.

---

## **The Orchestration Lifecycle**

1. **`jitsu serve`**: Initializes the `JitsuStateManager` and `ContextCompiler`.
2. **Setup**: The `ToolHandlers` are created (Dependency Injection) and registered with the `ToolRegistry`.
3. **Transport**: `run_server()` starts the MCP transport and the IPC background daemon.
4. **Call**: When an IDE agent calls a tool, the transport layer asks the Registry for the handler and executes it.

This design allows for high-fidelity testing of the orchestration logic in `handlers.py` while keeping the "messy" details of stdio communication isolated in `mcp_server.py`.
