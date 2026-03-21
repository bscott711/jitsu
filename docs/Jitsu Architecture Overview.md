# **Jitsu: JIT Context & Workflow Orchestrator**

**Jitsu** is a high-performance MCP (Model Context Protocol) server designed to eliminate "Prompt Debt" and "Context Drift" in AI-driven development. It serves as an intelligent bridge between a Python-based context engine and sandboxed IDE agents (such as Antigravity, Cursor, or Windsurf).

By shifting the heavy lifting of context preparation to Python, Jitsu ensures that agents receive only the "ground truth" of the codebase **Just-In-Time (JIT)**. This radically reduces token usage, prevents hallucination, and enables agents to work within massive repositories without overwhelming their context windows.

---

## **Core Philosophy**

1. **The Code is the Source of Truth:** Documents lie; code does not. Jitsu uses reflection, AST analysis, and schema extraction to provide the absolute current state of the project.
2. **Strict Typed Directives:** Agent instructions are validated Pydantic models (`AgentDirective`). They include explicit "Definitions of Done," verification commands, and strictly forbidden anti-patterns.
3. **Context-on-Demand (Progressive Disclosure):** Provide the agent with exactly what it needs for the *current* task. Agents can request additional context dynamically.
4. **Stateful Orchestration:** Jitsu maintains a persistent queue of phases, allowing agents to work through complex epics with a reliable source of state.
5. **Security via Lifecycle:** All destructive actions (commits, pushes) are governed by a "Just-based Git Lifecycle" to ensure project integrity.

---

## **Agentic Excellence**

Jitsu is designed to empower **Agentic Excellence**—the transition from passive LLM assistance to collaborative engineering. It enables agents to operate at the highest level of competence by providing a structured environment where natural language intent is systematically converted into verified implementation.

### **The Intelligence Core**

* **Intent-to-Plan Pipeline:** The `jitsu_plan_epic` tool allows agents to build a deterministic execution strategy. It breaks down complex user requests into discrete, manageable `AgentDirectives` that are logically sequenced and dependency-aware.
* **Mandatory Documentation Lifecycle:** A cornerstone of Agentic Excellence is the **Self-Documenting Workflow**. Jitsu mandates that significant codebase changes are accompanied by an update to the system's documentation (`README.md` and `docs/`). This requirement is baked into the Jitsu protocol, ensuring that human-readable knowledge evolves synchronously with the source.

---

## **Architecture Layers**

Jitsu operates through a strict five-layer Domain-Driven Design designed to maximize fidelity and code decoupling.

### **Layer 0: Strict Pydantic Models (The Domain)**

The zero-dependency foundation of Jitsu defines the communication protocol.

* **`AgentDirective`**: Defines a work phase, including instructions, anti-patterns, and context targets.
* **`PhaseReport`**: Structured feedback from the agent, including artifacts and verification results.
* **`TargetResolutionMode`**: Governs how the ContextCompiler handles specific files (`AUTO`, `STRUCTURE_ONLY`, `SCHEMA_ONLY`, `FULL_SOURCE`).

### **Layer 1: AST-First Providers (The Eyes)**

Providers (`jitsu.providers`) extract information from the filesystem using an AST-first policy.

* **`ASTProvider`**: Strips implementation details from Python files, providing structural skeletons.
* **`PydanticProvider`**: Uses live reflection to extract JSON schemas from models.
* **`DirectoryTreeProvider`**: Generates visual representations of the project structure.
* **`GitProvider`**: Analyzes the active repository using `git diff` and `git status`.

### **Layer 2: Core & State (The Engine)**

The `jitsu.core` module parses directives and manages task state.

* **`ContextCompiler`**: The engine weaves together directives and live codebase state into optimized Markdown prompts using **U-Curve Attention**.
* **`JitsuStateManager`**: Manages the life cycle of epics and phases, storing pending directives and aggregating completed phase reports.

### **Layer 3: Transport Layer (MCP Server)**

The top layer exposes Jitsu tools to IDEs.

* **Planning & Execution Tools**: An extensive tool suite of 10 core tools (including `jitsu_plan_epic`, `jitsu_check_coverage`, and `jitsu_get_next_phase`) allows agents to gather intelligence, verify coverage, and progress through epics.
* **Just-based Git Lifecycle**: Destructive operations are delegated to `just` recipes (`just commit`, `just sync`), providing a controlled security boundary.

### **Layer 4: CLI (The Bridge)**

The entry point for the user and integration with IDEs.

* **Typer CLI**: Minimalist CLI (`jitsu serve`) to start the orchestration server.
* **Global Configuration**: Manages environment variables and project-level settings.

---

## **The Orchestration Workflow**

1. **Plan**: Use `jitsu_get_planning_context()` to understand the repo and rules.
2. **Generate**: Use `jitsu_plan_epic()` to create a multi-phase implementation strategy.
3. **Submit**: Use `jitsu_submit_epic()` to load the plan into the server's queue.
4. **Pull**: Call `jitsu_get_next_phase()` to receive the first objective.
5. **Execute**: Modify the code as directed. Use `jitsu_request_context()` for missing info.
6. **Verify**: Run `just verify` to ensure tests, linting, and types are passing.
7. **Commit**: Use `jitsu_git_commit` to stage and commit changes.
8. **Report**: Call `jitsu_report_status()` to mark the phase as successful.

```mermaid
graph TD
    A[get_planning_context] --> B[plan_epic]
    B --> C[submit_epic]
    C --> D[get_next_phase]
    D --> E[Execution & Request Context]
    E --> F[just verify]
    F --> G[git_commit]
    G --> H[report_status]
    H --> D

---

## **Integrated Tool Collection**

Jitsu exposes a suite of **10 core tool components** that power its orchestration:
1. `ast`: Structural analysis and skeleton extraction.
2. `env_var`: Secure environment context resolution.
3. `file`: Raw text fallback for full source resolution.
4. `git`: Real-time repository state and lifecycle.
5. `markdown_ast`: Structural parsing of large documents.
6. `pydantic`: Schema-first intelligence for models.
7. `tree`: Navigational directory skeletonization.
8. `base`: The foundation for all provider implementations.
9. `registry`: Discovery and routing for tool handlers and providers.
10. `compiler`: Progressive disclosure and prompt weaving engine.
