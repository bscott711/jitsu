# **Jitsu: JIT Context & Workflow Orchestrator**

**Jitsu** (実 / "Truth/Substance") is a high-performance MCP (Model Context Protocol) server designed to eliminate "Prompt Debt" and "Context Drift" in AI-driven development. It serves as an intelligent bridge between a Python-based orchestration layer and sandboxed IDE agents (such as Antigravity, Cursor, or Windsurf).

By shifting the heavy lifting of context preparation to Python, Jitsu ensures that agents receive only the "ground truth" of the codebase **Just-In-Time (JIT)**. This radically reduces token usage, prevents hallucination, and enables agents to work within massive repositories without overwhelming their context windows.

---

## **Core Philosophy**

1. **The Code is the Source of Truth:** Documents lie; code does not. Jitsu uses reflection, AST analysis, and schema extraction to provide the absolute current state of the project.
2. **Strict Typed Directives:** Agent instructions are not just text; they are validated Pydantic models (`AgentDirective`). They include explicit "Definitions of Done," verification commands, and strictly forbidden anti-patterns.
3. **Context-on-Demand (Progressive Disclosure):** Provide the agent with exactly what it needs for the *current* task. If it discovers a dependency it didn't know it needed, it can request it dynamically.
4. **Inversion of Control:** The agent does not guess its next move. It "pulls" its next objective from Jitsu, executes it, and "pushes" back a report on success or failure.

---

## **System Architecture**

Jitsu operates through a multi-layered architecture designed to maximize fidelity while minimizing cost.

### **Layer 1: The Directive Engine (Domain Models)**

The heart of the system is the `AgentDirective`. This model defines the scope and constraints of a single work phase.

* **TargetResolutionMode**: Directives indicate how context should be resolved for each target:
  * `AUTO`: Use the intelligent AST-First fallback policy.
  * `STRUCTURE_ONLY`: Provide a summarized AST (signatures, docstrings) without implementation bodies.
  * `SCHEMA_ONLY`: Provide a Pydantic/JSON schema representation of a data model.
  * `FULL_SOURCE`: Provide the complete raw source code (fallback).

### **Layer 1.5: The Context Compiler (The Engine)**

The `ContextCompiler` is where the magic happens. It weaves together static instructions and dynamic codebase state into a single, highly-optimized Markdown prompt.

* **AST-First Policy**: When a target is in `AUTO` mode, the compiler attempts resolution in a specific priority sequence:
    1. **AST**: If the target is a `.py` file, provide a structural skeleton.
    2. **Pydantic**: If the target looks like a class or symbol, provide its JSON schema.
    3. **Tree**: If the target is a directory, provide a visual structure.
    4. **FileState**: As a final fallback, provide the full source text.
* **Context Manifests**: Every compiled prompt includes a manifest telling the agent *exactly* how its context was resolved (e.g., "Visual Tree Structure" vs "Full Source"). This meta-awareness helps the agent understand the level of detail it has.

### **Layer 2: Specialized Context Providers**

Providers are the "eyes" of Jitsu. They are modular and can be extended to support any file type or data source.

* **ASTProvider**: Uses Python's `ast` module to strip implementation details. **Token Savings: 70-90%** for large modules.
* **DirectoryTreeProvider**: Generates a filtered, visual tree of the file system, ignoring noisy directories like `.git` or `__pycache__`.
* **PydanticV2Provider**: Uses live reflection to extract schemas from Pydantic models.
* **FileStateProvider**: Reads raw disk content for non-Python or configuration files.

### **Layer 3: The Transport Layer (MCP Server)**

Jitsu exposes its capabilities to IDE agents via a standard Model Context Protocol interface.

* `jitsu_get_next_phase()`: Retrieves the next compiled JIT directive from the orchestrator queue.
* `jitsu_report_status()`: Submits a `PhaseReport` containing the outcome and verification output.
* `jitsu_request_context()`: Enables **Progressive Disclosure**. Agents can call this mid-task to resolve any unforeseen dependencies or explore the codebase on-demand without manual searching.

---

## **The Standard Agent Workflow**

1. **Pull**: Call `jitsu_get_next_phase()` to receive the current objective and initial context.
2. **Resolve**: If the initial context is insufficient, call `jitsu_request_context()` to drill down into specific files or modules.
3. **Code**: Implement changes based strictly on the directive's instructions and anti-patterns.
4. **Verify**: Run the `verification_commands` provided in the directive to ensure correctness.
5. **Status**: Call `jitsu_report_status()` to conclude the phase and allow the orchestrator to queue the next task.
