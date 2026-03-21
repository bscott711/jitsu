# Jitsu Ecosystem Landscape & SOTA Analysis

**Jitsu is a JIT Context Workflow Orchestrator** — an MCP server that acts as intelligent middleware between IDE coding agents (Cursor, Windsurf, Antigravity) and your codebase, rather than an autonomous agent itself. Its core thesis is that *context preparation* should be offloaded from the LLM's limited window to a high-performance Python engine, solving what it calls Prompt Debt, Context Drift, and LLM Laziness.

---

## What Jitsu Actually Is

Jitsu is best understood as an **inversion-of-control layer for IDE agents** — instead of the agent passively receiving static context, it must actively *pull* structured, JIT-compiled directives from Jitsu's MCP server. Its architecture is four layers:

- **Layer 0 (Domain)**: Immutable Pydantic V2 models — `AgentDirective`, `PhaseReport`, `TargetResolutionMode` — forming the zero-dependency communication protocol.
- **Layer 1 (Providers)**: AST-first filesystem adapters (`ASTProvider`, `PydanticProvider`, `GitProvider`, `DirectoryTreeProvider`) that strip implementation noise from context.
- **Layer 2 (Core)**: The `ContextCompiler`, `JitsuStateManager`, and `JitsuPlanner` — handles epic lifecycles and U-Curve prompt assembly.
- **Layer 3 (Transport)**: A pure stdio/JSON-RPC MCP server and minimal Typer CLI exposing orchestration tools.

---

## Core Innovations vs. SOTA

### U-Curve Context Compilation

Jitsu's most distinctive technical claim is its **U-Curve XML prompt structure**: critical instructions are placed at the edges of the context window (`<INSTRUCTIONS>` first, `<TASK_AND_OUTPUT_SPEC>` last), with heavy context dumps in the middle trough. This directly targets the well-documented "Lost in the Middle" problem — research from 2023 confirmed that LLMs using positional encodings like RoPE exhibit a performance dead zone for tokens in the middle of long contexts. The U-Curve approach is a concrete, tested implementation of a mitigation strategy that most SOTA agents only acknowledge conceptually.

### AST-First Progressive Disclosure

Rather than dumping raw source, the `ASTProvider` surgically extracts structural skeletons (classes, signatures, docstrings) for 70–90% token savings. Jitsu's approach is architecturally explicit — it encodes the disclosure policy directly into `TargetResolutionMode` (`AUTO`, `STRUCTURE_ONLY`, `SCHEMA_ONLY`, `FULL_SOURCE`) so the planner makes deliberate per-file token budget decisions.

### Structured Directives with Definitions of Done

Every phase is delivered as a validated `AgentDirective` with explicit `completion_criteria`, `anti_patterns`, and `verification_commands`. Jitsu takes the Agent-Computer Interface (ACI) concept further by encoding *what success looks like* in the directive itself — the Pydantic model becomes a contract, not just a message.

### Recovery Loop with Traceback Expansion

When verification fails, Jitsu dynamically parses the traceback, extracts local file paths, and injects those files (`FULL_SOURCE`) into the retry context — augmenting rather than overwriting the base message. This traceback-driven dynamic context expansion is a surgical mechanism that respects the module scope boundary.

---

## SOTA Landscape Comparison

| Dimension | Jitsu | SWE-Agent | OpenHands | Claude Code / Aider |
| :--- | :--- | :--- | :--- | :--- |
| **Architecture** | MCP middleware / orchestrator | Autonomous agent + ACI | Autonomous agent + CodeAct | Autonomous agent |
| **Context strategy** | U-Curve XML + AST-first JIT | ACI output filtering | Summarization + CodeAct | Compaction, CLAUDE.md anchoring |
| **State persistence** | SQLite Epic queue, survives restarts | Session-scoped | Docker sandbox + session state | Session memory |
| **Execution model** | Pull-based (agent calls `jitsu_get_next_phase`) | Push (agent acts autonomously) | Push (CodeAct) | Push |
| **Validation** | Pydantic DoD + `just verify` | SWE-bench eval harness | Docker isolation | Test runner integration |
| **Sandboxing** | `just`-based Git lifecycle | Shell in controlled env | Docker per-session | None (trust-based) |
| **Multi-agent** | Single orchestrator (planned) | Single agent | Full hierarchical delegation | N/A |

---

## Where Jitsu Leads the Field

- **The "Slim Refactor" Continuity**: Jitsu deliberately *removed* its internal executor to become a pure context server, matching emerging best practices where IDE agents are anchored to an MCP-based reference state to reduce code drift.
- **Self-Documenting Workflow**: The Planner requires documentation updates as a mandatory Epic phase, treating docs as code. This addresses the divergence between agentic changes and human-readable knowledge.

---

## Gaps vs. SOTA

- **No Benchmark Evaluation**: No current measurement on SWE-bench or similar harnesses (where SOTA agents hit 74–88%).
- **No Autonomous Execution**: Requires a human-driven IDE agent; cannot self-loop on a task without one.
- **No Vector/Semantic Retrieval**: Context selection is structural and explicit; lacks semantic RAG capabilities for cross-module discovery.
- **No Multi-agent Concurrency**: Roadmap item, but currently absent compared to OpenHands' delegation.
- **Python-centric**: Tightly coupled to Python tooling (`uv`, `just`, `ruff`, `pyright`).

---

## Bottom Line
