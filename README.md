# **Jitsu (実)**

## AST-First, Strictly-Typed JIT Context & Workflow Orchestrator for AI IDEs via MCP

Jitsu (実 / "Truth") eliminates **Prompt Debt** and **Context Drift** in AI IDEs (Antigravity, Cursor, Windsurf). Instead of relying on static, stale instruction files, Jitsu compiles the "ground truth" of your codebase **Just-In-Time (JIT)** and serves it directly to your agent's context window via the Model Context Protocol (MCP).

---

## **The Core Value**

- **AST-First Context**: Jitsu doesn't just read files; it parses Python AST to provide structural "skeletons" (signatures, docstrings, constants) while stripping implementation noise.
- **Strictly-Typed Directives**: Every task is a validated Pydantic V2 model. No more vague instructions or "guesswork" for the agent.
- **Definition of Done (DoD)**: Every directive includes explicit `completion_criteria` and `verification_commands` to ensure quality.
- **Progressive Disclosure**: Agents use the `jitsu_request_context` tool to dynamically request class schemas or source code on-demand as they discover dependencies.
- **Inversion of Control**: The IDE agent doesn't decide what to do next; it asks Jitsu for its current assignment, executes it, and reports back.

---

## **Installation**

Jitsu is built for `uv`:

```bash
uv pip install -e .
```

---

## **The Jitsu Workflow**

### **1. Start the Jitsu Server**

Launch the MCP server to listen for IDE agent connections:

```bash
uv run jitsu serve
```

### **2. Submit an Epic**

Feed a sequence of tasks (Phases) into a running Jitsu server from any terminal:

```bash
uv run jitsu submit --epic/epics/test_logic.json
```

### **3. Execute in the IDE**

In your AI agent prompt, use the Jitsu MCP tools:

1. **`jitsu_get_next_phase()`**: Receive your task and JIT-compiled context.
2. **`jitsu_request_context(target="...")`**: Request deep context if discovery reveals missing imports.
3. **`jitsu_report_status()`**: Submit your findings and verification logs to move to the next phase.

---

## **Architecture**

Jitsu uses a **Layered Provider Pattern** to synthesize context:

- **Layer 1 (Directives)**: Pydantic-validated task models.
- **Layer 1.5 (Compiler)**: AST-First resolution policy with `AUTO` fallback logic.
- **Layer 2 (Providers)**: `AST`, `PydanticV2`, and `FileState` resolution engines.
- **Layer 3 (MCP Server)**: Progressive disclosure transport layer.

---

## **Development**

Run tests:

```bash
uv run pytest
```

Linting:

```bash
uv run ruff check .
```
