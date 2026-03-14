# **Jitsu**

## **JIT Context & Workflow Orchestrator for AI IDEs**

**Jitsu** is a high-performance orchestration layer designed to eliminate **Prompt Debt**, **Context Drift**, and **LLM Laziness** in AI-driven software engineering. It shifts context preparation from the agent's limited window to a powerful Python engine, serving the absolute "ground truth" of your codebase **Just-In-Time (JIT)** directly to your AI IDE.

### **✨ v0.4.0 Architecture Highlights**

Jitsu operates as a stateful memory and context engine for your IDE agent:

* **U-Curve Context Compilation:** Mathematically optimized prompt construction that forces critical instructions to the edges of the context window, eliminating the LLM "Lost in the Middle" syndrome.  
* **AST-Aware Intelligence:** Jitsu surgically extracts the structural skeletons (AST) of your files, providing 70-90% token savings while maintaining high-fidelity architectural context.  
* **Pydantic Gatekeepers:** Directives are delivered as ironclad, validated Pydantic models with explicit "Definitions of Done," verification commands, and anti-patterns.
* **Persistent Task Queue:** Maintain complex state across IDE restarts. Jitsu keeps track of your Epic's progress and the absolute "ground truth" of completed phases.

## **🤖 Agentic Excellence**

Jitsu is designed to empower **Agentic Excellence**—the transition from passive LLM assistance to collaborative, state-aware engineering. It transforms high-level natural language intent into a structured, verified implementation loop within IDEs like Antigravity, Cursor, and Windsurf.

### **The Collaborative Workflow**

Jitsu handles the heavy lifting of context management and state tracking:

1. **Natural Language Intent:** You provide a goal to your IDE agent.
2. **Deterministic Planning:** Use the `jitsu_plan_epic` tool to analyze the codebase and generate a multi-phase `Epic`.
3. **JIT Context Compilation:** For each phase, Jitsu surgically compiles the absolute minimum context required, optimized via **U-Curve Attention**.
4. **Verified Completion:** Every phase includes mandatory verification via `just verify` to ensure 100% coverage and zero technical debt.
5. **Self-Documentation:** Jitsu mandates that documentation updates are part of the implementation cycle to ensure knowledge is always current.

> [!NOTE]
> **Self-Documentation Guarantee:** Jitsu treats documentation as code. Every Epic concluded using Jitsu includes a final step to synchronize architectural docs, ensuring your wiki never goes stale.

## **🚀 Quick Start**

### **Installation**

Jitsu is optimized for `uv`:

```bash
uv tool install jitsu
```

### **IDE Integration (MCP)**

To use Jitsu in an MCP-compatible IDE (Antigravity, Cursor, Windsurf, etc.):

1. **Configure MCP**: Add `jitsu serve` as an MCP server using `stdio` transport.
2. **Load an Epic**: Optional pre-loading of an existing plan:

   ```bash
   jitsu serve --epic path/to/epic_plan.json
   ```

3. **Orchestrate**: Drive your agent using the **9 Core Jitsu Tools**:
   * `jitsu_get_planning_context`
   * `jitsu_plan_epic`
   * `jitsu_submit_epic`
   * `jitsu_get_next_phase`
   * `jitsu_report_status`
   * `jitsu_inspect_queue`
   * `jitsu_request_context`
   * `jitsu_git_status`
   * `jitsu_git_commit`

## **📖 Documentation**

For a deep dive into Jitsu's architecture and capabilities, visit our [**Wiki**](docs/index.md).

* [**Architecture Overview**](docs/index.md#4-layer-architecture): The 4-layer stack.
* [**Ecosystem Landscape & SOTA**](docs/architecture/landscape.md): Comparative analysis vs. SOTA agents.
* [**CLI Reference**](docs/CLI%20Reference.md): Typer CLI usage for `serve`.
* [**MCP Tools Reference**](docs/MCP%20Tools%20Reference.md): Detailed documentation for the 9 core orchestrator tools.

## **🛠️ Development**

Jitsu is built with a strictly enforced "Zero-Regression" policy:  

```bash
just verify
```

*Includes: Ruff (Linting), Pyright (Types), Pytest (100% Coverage), and Deptry (Dependencies).*
