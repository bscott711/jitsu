# **Jitsu (実)**

## **AST-First, Self-Orchestrating JIT Context for AI IDE Agents**

**Jitsu** (実 / "Truth") is a powerful orchestration layer designed to eliminate **Prompt Debt** and **Context Drift** in AI-capable IDEs. It shifts context preparation from the agent's limited window to a high-performance Python engine serving the absolute "ground truth" of your codebase **Just-In-Time (JIT)**.

---

## **🚀 Quick Start**

### **Installation**

Jitsu is optimized for `uv`:

```bash
uv tool install jitsu
```

### **Core Workflow**

1. **Serve**: `uv run jitsu serve`
2. **Plan & Submit**: Draft an `epic.json` and run `uv run jitsu submit epic.json`
3. **Orchestrate**: Use your favorite IDE (Antigravity, Cursor, etc.) to pull phases via `jitsu_get_next_phase`.

---

## **📖 Documentation**

For a deep dive into Jitsu's architecture and capabilities, visit our **[Wiki](docs/index.md)**.

- [**Architecture Overview**](docs/index.md#4-layer-architecture): The 4-layer stack from Models to MCP.
- [**CLI Reference**](docs/CLI%20Reference.md): Typer CLI usage for `init`, `serve`, and `submit`.
- [**MCP Tools**](docs/MCP%20Tools%20Reference.md): Reference for the 8 default orchestrator tools.

---

## **🛠️ Development**

Jitsu is built with a "Zero-Regression" policy:

```bash
just verify
```

*Includes: Ruff (Linting), Pyright (Types), Pytest (100% Coverage), and Deptry (Dependencies).*
