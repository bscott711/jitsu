# **Jitsu**

## **Autonomous, AST-Aware, Self-Healing AI Engineering Agent**

**Jitsu** is an orchestration layer designed to eliminate **Prompt Debt**, **Context Drift**, and **LLM Laziness** in AI-driven software engineering. It shifts context preparation from the agent's limited window to a high-performance Python engine, serving the absolute "ground truth" of your codebase **Just-In-Time (JIT)**.

### **✨ v0.2.0 Architecture Highlights**

Jitsu operates as a deterministic, engineer with a built-in safety net:

* **U-Curve Context Compilation:** Mathematically optimized prompt construction that forces critical instructions to the edges of the context window, eliminating the LLM "Lost in the Middle" syndrome.  
* **AST-Aware Recovery Loop:** If a test fails, Jitsu doesn't just guess why. It surgically extracts the traceback, resolves the Abstract Syntax Tree (AST) of the failing file, and injects it into a recovery prompt for a zero-hallucination fix.  
* **Pydantic Gatekeepers:** Ironclad output validation instantly rejects LLM laziness (e.g., \# rest of code here or ...), forcing the model to generate 100% complete, executable code before it ever touches your disk.  
* **Zero-Bypass Engineering:** Jitsu strictly adheres to a "Zero-Regression" policy, enforcing 100% test coverage with zero \# noqa or \# type: ignore linting bypasses.

## **🚀 Quick Start**

### **Installation**

Jitsu is optimized for uv:

```bash
uv tool install jitsu
```

### **Core Workflows**

**1\. Autonomous Execution (New in v0.2.0)**  
Let Jitsu act as a fully autonomous agent. It will plan the Epic, compile the context, execute the edits, and run the verification loops itself.  
jitsu auto "Refactor the core orchestrator to use the new State Manager"

**2\. The IDE Integration (MCP)**  
If you prefer to drive via an MCP-compatible IDE (Antigravity, Cursor, etc.):

1. **Serve**: uv run jitsu serve  
2. **Plan & Submit**: Draft an epic.json and run uv run jitsu submit epic.json  
3. **Orchestrate**: Use your IDE to pull phases via the jitsu\_get\_next\_phase tool.

## **📖 Documentation**

For a deep dive into Jitsu's architecture and capabilities, visit our [**Wiki**](docs/index.md).

* [**Architecture Overview**](docs/index.md#4-layer-architecture): The execution stack (Planner \-\> Context Compiler \-\> Executor \-\> Storage).  
* [**CLI Reference**](docs/CLI%20Reference.md): Typer CLI usage for auto, init, serve, and submit.  
* [**MCP Tools**](docs/MCP%20Tools%20Reference.md): Reference for the default orchestrator tools.

## **🛠️ Development**

Jitsu is built with a strictly enforced "Zero-Regression" policy:  

```bash
just verify
```

*Includes: Ruff (Linting), Pyright (Types), Pytest (100% Coverage), and Deptry (Dependencies).*
