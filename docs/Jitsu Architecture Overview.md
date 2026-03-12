# **Jitsu: JIT Context & Workflow Orchestrator**

**Jitsu** is a high-performance MCP (Model Context Protocol) server designed to eliminate "Prompt Debt" and "Context Drift" in AI-driven development. It serves as an intelligent bridge between a Python-based orchestration layer and sandboxed IDE agents (such as Antigravity, Cursor, or Windsurf).

By shifting the heavy lifting of context preparation to Python, Jitsu ensures that agents receive only the "ground truth" of the codebase **Just-In-Time (JIT)**. This radically reduces token usage, prevents hallucination, and enables agents to work within massive repositories without overwhelming their context windows.

---

## **Core Philosophy**

1. **The Code is the Source of Truth:** Documents lie; code does not. Jitsu uses reflection, AST analysis, and schema extraction to provide the absolute current state of the project.
2. **Strict Typed Directives:** Agent instructions are validated Pydantic models (`AgentDirective`). They include explicit "Definitions of Done," verification commands, and strictly forbidden anti-patterns.
3. **Context-on-Demand (Progressive Disclosure):** Provide the agent with exactly what it needs for the *current* task. Agents can request additional context dynamically.
4. **Self-Orchestration:** Jitsu enables an autonomous loop where agents can plan their own tasks, queue phases, and report progress without human intervention.
5. **Security via Lifecycle:** All destructive actions (commits, pushes) are governed by a "Just-based Git Lifecycle" to ensure project integrity.

---

## **The 1.0 Architecture**

Jitsu operates through a strict four-layer Domain-Driven Design designed to maximize fidelity, autonomy, and code decoupling. Dependencies flow in one direction: inwards.

### **Layer 0: Strict Pydantic Models (The Domain)**

The zero-dependency foundation of Jitsu is a set of rigorous Pydantic models (`jitsu.models`) that define the communication protocol between the orchestrator and the agent.

* **`AgentDirective`**: Defines a work phase, including instructions, anti-patterns, and context targets.
* **`PhaseReport`**: Structured feedback from the agent, including artifacts and verification results.
* **`TargetResolutionMode`**: Governs how the ContextCompiler handles specific files (`AUTO`, `STRUCTURE_ONLY`, `SCHEMA_ONLY`, `FULL_SOURCE`).

### **Layer 1: Core & State (The Engine)**

The `jitsu.core` module parses the directives and manages the state of the agent's tasks.

* **`ContextCompiler`**: The engine weaves together directives and live codebase state into optimized Markdown prompts. It includes **Context Manifests** on every compile to explicitly tell the agent how each target was resolved.
* **`JitsuStateManager`**: Manages the life cycle of epics and phases, storing pending directives and aggregating completed phase reports.

### **Layer 2: AST-First Providers (The Eyes)**

Providers (`jitsu.providers`) are specialized adapters that extract information from the filesystem and environment using an AST-first policy.

* **`FileStateProvider` (`file`)**: Fallback for full source code text.
* **`ASTProvider` (`ast`)**: Strips implementation details from Python files, providing structural skeletons. **Token Savings: 70-90%**.
* **`PydanticProvider` (`pydantic`)**: Uses live reflection to extract JSON schemas from models.
* **`DirectoryTreeProvider` (`tree`)**: Generates visual representations of the project structure.
* **`GitProvider` (`git`)**: Analyzes the active repository using `git diff` and `git status --short`.
* **`MarkdownASTProvider` (`markdown_ast`)**: Extracts headings and code blocks from large markdown files for structural previews.
* **`EnvVarProvider` (`env_var`)**: Safely exposes necessary environment configurations.

### **Layer 3: Decoupled Transport Layer (MCP Server & CLI)**

The top layer (`jitsu.server` & `jitsu.cli`) exposes Jitsu to IDEs and handles the execution loop. It is completely decoupled from domain logic via Dependency Injection.

* **Dynamic Tool Registry (`registry.py` & `handlers.py`)**: The MCP Server (`mcp_server.py`) acts purely as a transport mechanism (stdio/JSON-RPC). It delegates all tool execution to a dynamic `ToolRegistry` and injected `ToolHandlers`, preventing God-Module anti-patterns.
* **Planning & Execution Tools**: An extensive tool suite (`jitsu_get_planning_context`, `jitsu_submit_epic`, `jitsu_request_context`) allows agents to gather intelligence and queue future phases dynamically (*Progressive Disclosure*).
* **Two-Way IPC Handshake**: A background TCP daemon (`jitsu serve`) constantly listens for new epics via `jitsu submit`, seamlessly injecting them into the running MCP server.
* **Just-based Git Lifecycle**: Destructive operations are delegated to `just` recipes (`just commit`, `just sync`), providing a controlled security boundary.

---

## **The Autonomous Workflow Loop**

1. **Plan**: Use `jitsu_get_planning_context()` to understand the repo and rules.
2. **Submit**: Run `jitsu submit epic.json` from your terminal to feed phases to the background server.
3. **Pull**: Call `jitsu_get_next_phase()` to receive the first objective.
4. **Execute**: Modify the code as directed. Use `jitsu_request_context()` for missing info.
5. **Verify**: Run `just verify` to ensure tests, linting, and types are passing.
6. **Commit**: Use `jitsu_git_commit` to stage and commit changes.
7. **Report**: Call `jitsu_report_status()` to mark the phase as successful and move to the next.

```mermaid
graph TD
    A[get_planning_context] --> B[Generate Plan]
    B --> C[submit_epic]
    C --> D[get_next_phase]
    D --> E[Execution & Request Context]
    E --> F[just verify]
    F --> G[git_commit]
    G --> H[report_status]
    H --> D
