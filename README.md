# **Jitsu (実)**

## **AST-First, Self-Orchestrating JIT Context for AI IDE Agents**

**Jitsu** (実 / "Truth") is a powerful orchestration layer designed to eliminate **Prompt Debt** and **Context Drift** in AI-capable IDEs (such as Antigravity, Cursor, or Windsurf). It shifts the workload from the agent's limited context window to a high-performance Python engine that serves the absolute "ground truth" of your codebase **Just-In-Time (JIT)**.

---

## **Why Jitsu?**

Jitsu transitions AI agents from passive code generators to **self-orchestrating collaborators**:

- **AST-First Context**: Jitsu prioritizes structural AST "skeletons" (signatures, docstrings, constants) over raw source code, stripping away implementation noise to save up to **90% of tokens**.
- **Self-Orchestration**: Agents are no longer just task-takers. With tools like `jitsu_get_planning_context` and `jitsu_submit_epic`, agents can plan their own work, breaking down complex objectives into validated execution phases.
- **Strict Typed Directives**: Instructions are delivered as validated Pydantic models with explicit "Definitions of Done," verification commands, and strictly forbidden anti-patterns.
- **Managed Git Lifecycle**: All changes are governed by a "Just-based Git Lifecycle" (`jitsu_git_commit`), ensuring that every change is verified and committed following [Conventional Commits](https://www.conventionalcommits.org/).
- **Progressive Disclosure**: Agents can pull context on-demand as they discover dependencies, rather than being overwhelmed by a massive, static prompt.

---

## **Core Technology**

- **Layered Architecture**: A 4-layer stack covering everything from strict domain models to a self-orchestrating MCP server.
- **Intelligent Fallback**: The `ContextCompiler` automatically falls back from AST to Pydantic schemas, directory trees, or full source based on the requested target.
- **Model Context Protocol (MCP)**: Native integration with the industry-standard protocol for connecting AI models to local tools and data.

---

## **Installation**

Jitsu is optimized for use with `uv`. For global access, we recommend:

```bash
uv tool install jitsu
```

For local development:

```bash
git clone https://github.com/bscott711/jitsu
cd jitsu
uv pip install -e .
```

---

## **The Jitsu Workflow**

1. **Serve**: Start the MCP server securely in the background (or hook into your IDE config):

   ```bash
   uv run jitsu serve
   ```

2. **Plan**: Draft an `epic.json` file detailing your phases, module scopes, and validation logic.
3. **Submit**: Push the epic seamlessly to the active server over IPC:

   ```bash
   uv run jitsu submit path/to/epic.json
   ```

4. **Pull**: The agent calls `jitsu_get_next_phase()` to receive its first atomic directive.
5. **Execute & Verify**: The agent implements changes and requests Progressive Disclosure via `jitsu_request_context` when needed. It then runs `just verify` to ensure quality.
6. **Commit**: The agent uses `jitsu_git_commit` to stage and commit the verified work.
7. **Report**: The agent calls `jitsu_report_status()` to mark the phase as complete and move to the next.

---

## **Documentation**

- [**Jitsu Architecture Overview**](docs/Jitsu%20Architecture%20Overview.md): Deep dive into the 1.0 multi-layered design and the autonomous loop.
- [**CLI Command Reference**](docs/CLI%20Reference.md): Explore the Typer CLI `init`, `serve`, `submit`, and `queue` commands.
- [**MCP Tools Reference**](docs/MCP%20Tools%20Reference.md): Reference for the 8 default tools shipped with the Jitsu orchestrator.

---

## **Development**

Jitsu is built with a "Zero-Regression" policy, maintained via strict verification:

```bash
just verify
```

*Includes: Ruff (Linting), Pyright (Types), Pytest (100% Coverage), and Deptry (Dependencies).*
