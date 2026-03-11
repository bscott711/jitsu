# **Jitsu (実)**

## **AST-First, Strictly-Typed JIT Context & Workflow Orchestrator for AI IDEs via MCP**

**Jitsu** (実 / "Truth") is a powerful orchestration layer designed to eliminate **Prompt Debt** and **Context Drift** in AI-capable IDEs (such as Antigravity, Cursor, or Windsurf). It ensures that your AI agents work with high-fidelity, just-in-time context, guided by rigid execution constraints.

---

## **Why Jitsu?**

Most AI agents struggle with large codebases because they are overwhelmed by too much context or hallucinate due to too little. Jitsu solves this by:

- **AST-First Context**: Instead of dumping raw files, Jitsu parses Python source code to provide structural "skeletons" (signatures, docstrings, and constants), stripping away implementation noise to save up to **90% of tokens**.
- **Strict Typed Directives**: Tasks are defined as validated Pydantic V2 models (`AgentDirective`). No more vague instructions—agents receive explicit phases with mapped context.
- **Definition of Done (DoD)**: Every task includes mandatory `completion_criteria` and `verification_commands`. The agent cannot simply "finish"; it must prove its work.
- **Progressive Disclosure**: Agents use the `jitsu_request_context` tool to dynamically request class schemas or source code on-demand as they discover dependencies during execution.
- **Inversion of Control**: The agent doesn't decide what to do next. It "pulls" its next objective from Jitsu, executes, and reports back a structured `PhaseReport`.

---

## **Core Technology**

- **Agnostic Context Compiler**: A multi-layered resolution engine that handles AST structural analysis, Pydantic schema extraction, and directory tree visualization with a smart fallback to raw source.
- **Two-Way IPC Handshake**: A rock-solid anyio-powered TCP daemon allows external CLI tools to push "Epics" (sequences of phases) into a running MCP server in real-time.
- **Model Context Protocol (MCP)**: Native integration with the industry-standard protocol for connecting AI models to local tools and data.

---

## **Installation**

Jitsu is optimized for use with `uv`:

```bash
uv pip install -e .
```

---

## **The Jitsu Workflow**

### **1. Launch the Server**

Start the MCP server to listen for IDE agent connections:

```bash
uv run jitsu serve
```

### **2. Submit an Epic**

From another terminal, feed a sequence of tasks (an "Epic") into the running server:

```bash
uv run jitsu submit --epic epics/your_epic.json
```

### **3. Collaborate in the IDE**

In your AI agent's chat, the following tools are now available via the MCP server:

1. **`jitsu_get_next_phase()`**: Receive your next task and its JIT-compiled context.
2. **`jitsu_request_context()`**: If you discover a missing dependency, resolve it on-demand.
3. **`jitsu_report_status()`**: Submit your findings and verification logs to unlock the next phase in the Epic.

---

## **Documentation**

Explore the detailed documentation for Jitsu's core tools:

- [**`jitsu_get_next_phase`**](docs/tool_jitsu_get_next_phase.md): The entry point for pulling instruction-rich JIT context.
- [**Jitsu Architecture Overview**](docs/Jitsu%20Architecture%20Overview.md): Deep dive into the multi-layered design.

---

## **Development**

Fully verified with 100% test coverage:

```bash
just verify
```

*Includes: Ruff (Linting), Pyright (Types), Pytest (100% Coverage), and Deptry (Dependencies).*
