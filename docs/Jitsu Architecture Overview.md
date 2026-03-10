# **Jitsu: JIT Context & Workflow Orchestrator**

**Jitsu** (実 / "Truth/Substance") is an MCP (Model Context Protocol) server designed to eliminate "Prompt Debt" and "Context Drift" in AI IDEs. It serves as a bridge between an external Python orchestrator and sandboxed IDE agents (such as Antigravity, Cursor, or Windsurf).

Instead of overwhelming agents with massive context windows or relying on stale documentation, Jitsu compiles the "ground truth" of your codebase **Just-In-Time (JIT)**. This shifts the heavy lifting of context preparation to Python, significantly reducing token usage and improving agent reliability.

## **Core Philosophy**

1. **The Code is the Source of Truth:** Documents lie; code does not. Jitsu uses Python's AST and reflection to extract the exact state of the project.
2. **Strict Directives:** Agent instructions are typed, validated Pydantic models. They include explicit definitions of done, verification commands, and banned anti-patterns.
3. **Context-on-Demand:** Only provide the agent with exactly what it needs for the current task. If it needs more, it can request it progressively via MCP tools.
4. **Inversion of Control:** The agent does not guess its next task. It asks Jitsu for its next phase, executes it, and reports the outcome.

## **System Architecture**

Jitsu operates through a layered architecture that ensures high-fidelity context with minimal token overhead.

### **Layer 1: The Directive Engine (Domain Models)**

Everything starts with the `AgentDirective`. This Pydantic model defines the scope of a task.

* **TargetResolutionMode**: Directives specify how context should be resolved for each target:
  * `AUTO`: Use the AST-First policy to find the best representation.
  * `STRUCTURE_ONLY`: Provide a summarized AST (function signatures, class definitions) without implementation details.
  * `SCHEMA_ONLY`: Provide a Pydantic/JSON schema representation of a data model.
  * `FULL_SOURCE`: Provide the complete raw source code.

### **Layer 1.5: The Context Compiler**

The `ContextCompiler` is the engine that weaves directives and codebase state into a single Markdown prompt.

* **AST-First Policy**: For `AUTO` resolution, the compiler attempts to resolve targets in order: `AST` -> `Pydantic` -> `FileState`. It prioritizes structural logic over raw text.
* **Context Manifest**: Every compiled prompt includes a "Compiled Context Manifest" at the end, telling the agent exactly which providers were used to resolve its context (e.g., "Summarized (Structural AST)").

### **Layer 2: Context Providers**

Jitsu uses specialized providers to "read" the codebase:

* **ASTProvider**: Uses Python's `ast` module to strip away implementation bodies, leaving only the "skeleton" (signatures, docstrings, and constants).
* **PydanticV2Provider**: Extracts JSON schemas from live Pydantic models, perfect for data-heavy tasks.
* **FileStateProvider**: A raw fallback that reads the disk content for files that do not support structural analysis.

### **Layer 3: The MCP Transport Layer**

Jitsu exposes a suite of MCP tools that the IDE agent uses to communicate with the orchestrator:

* `jitsu_get_next_phase()`: Retrieves the next compiled JIT directive.
* `jitsu_report_status()`: Submits a `PhaseReport` with success/failure, notes, and verification output.
* `jitsu_request_context()`: Enables **Progressive Disclosure**. If an agent discovers it needs a specific class schema or file while working, it calls this to inject that context into its current session on-demand.

## **The Agent Loop**

The standard operating procedure for a Jitsu-powered agent is simple:

1. **Identify**: Call `jitsu_get_next_phase()` to receive constraints and truth.
2. **Expand**: If a dependency is missing, call `jitsu_request_context()` to resolve it.
3. **Execute**: Implement changes based on the directive.
4. **Verify**: Run the `verification_commands` provided in the directive.
5. **Report**: Call `jitsu_report_status()` to conclude the phase.
