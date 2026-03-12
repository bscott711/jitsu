# **Layer 1: Core Engine**

Layer 1 is the "Engine Room" of Jitsu. It implements the logic required to parse directives, manage the state of the execution queue, and compile optimized JIT context manifests for the agent.

---

## **Key Components**

### **`ContextCompiler`**

The `ContextCompiler` is responsible for weaving `AgentDirectives` and live codebase state into single, high-fidelity Markdown prompts. It implements the **Progressive Disclosure** strategy.

#### **AST-First & AUTO Fallback**

The compiler uses an intelligent `AUTO` resolution strategy to maximize context value while minimizing token usage:

1. **AST (`ast`)**: Attempts to provide structural skeletons (signatures, docstrings) of Python files.
2. **Pydantic (`pydantic`)**: Falls back to JSON schema extraction for internal Jitsu models.
3. **Preferred Provider**: Respects the explicitly requested provider if specified.
4. **FileState (`file`)**: Final fallback to full source code if structural analysis is unavailable or insufficient.

This logic ensures agents receive the "Skeleton" of the code by default, saving up to 90% of tokens, while still having access to full source when necessary.

### **`JitsuStateManager`**

The `JitsuStateManager` manages the in-memory state of the entire orchestration loop. It acts as the bridge between the transport layer (MCP/CLI) and the execution history.

#### **Responsibilities**

- **Queue Management**: Stores pending `AgentDirectives` submitted via IPC.
- **Phase Handover**: Delivers the next directive to the agent via `get_next_directive()`.
- **Status Tracking**: Records `PhaseReports` and aggregates progress across an entire Epic.
- **Epic Awareness**: Tracks remaining phases within an epic to provide the agent with a sense of completion.

---

## **The Orchestration Loop**

Layer 1 facilitates the following loop:

1. **State Manager** receives an Epic.
2. **Agent** pulls the next `AgentDirective`.
3. **Compiler** resolves the requested `ContextTargets` via Layer 2 Providers.
4. **Agent** executes work and returns a `PhaseReport`.
5. **State Manager** updates the status and prepares the next phase.
