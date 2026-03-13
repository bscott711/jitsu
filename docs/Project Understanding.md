# **Jitsu: Project Understanding & Architecture**

As the lead dev, here is my explicit understanding of our system, architecture, and the strict rules we are operating under.

## **The Core Mission**

We are building an autonomous, self-healing execution engine AND an inversion of control for AI agents (Antigravity, Cursor, Windsurf). Currently, agents suffer from "Context Drift"—they rely on static files that become outdated, leading to hallucinations, infinite error loops, and LLM laziness.  
Jitsu solves this in two ways:

1. **Autonomous Execution (jitsu auto)**: Operating as a Staff-level AI engineer, Jitsu plans Epics, compiles context Just-In-Time (JIT), executes edits, and runs its own AST-aware recovery loops when tests fail.  
2. **MCP Orchestration (jitsu serve)**: Forcing IDE-based agents to connect via the Model Context Protocol (MCP) and ask for their next phase, guaranteeing they only ever act on the dynamic, ground-truth state of the codebase.

## **Architectural Layers (Strict Domain-Driven Design)**

We enforce a one-way dependency flow to ensure the system remains perfectly decoupled:  
Layer 0 \- The Directive Engine (jitsu.models): Pure, strict Pydantic V2 schemas (AgentDirective, PhaseReport, ContextTarget, FileEdit). This is our core domain. It knows nothing about the outside world. Immutability (frozen=True) and strict typing are mandatory. This layer also acts as our **Pydantic Gatekeeper**, using strict validators to instantly reject LLM laziness (e.g., \# rest of code here or ...).  
Layer 1 \- Core & State (jitsu.core): The ContextCompiler, JitsuExecutor, JitsuPlanner, and JitsuStateManager. This layer orchestrates the logic. It implements the **U-Curve Context Architecture** (forcing critical instructions to the absolute edges of the prompt) and the **AST-Aware Recovery Loop** (extracting tracebacks and resolving structural outlines to surgically patch code on verification failure).  
Layer 2 \- The Providers (jitsu.providers): The adapters that inspect the real world. FileStateProvider, AST dumpers, Pydantic schema extractors, Markdown structural parsers, Git analyzers, and EnvVar readers. This layer MUST be AST-First to strip noise out of the LLM context.  
Layer 3 \- The Transport Layer (jitsu.server & jitsu.cli): The Typer CLI, background IPC daemon, and the MCP stdio server. It translates the external world into our core domain. Progressive Disclosure via dynamically responding to jitsu\_request\_context requests and managing the full jitsu auto lifecycle is handled here.

## **Coding Rules & Engineering Standards**

To keep this project rock solid, we adhere strictly to the following rules:  
100% Test Coverage & Symmetrical Engineering: Mandatory. We do not merge or finalize features if coverage drops below 100%, including edge cases and hidden exception pathways. Every architectural change must be paired with its corresponding test suite update.  
Zero Linter Bypasses: We operate with a strict zero-bypass policy. Absolutely no \# noqa, \# type: ignore, or \# pyright: ignore comments are allowed in the codebase. We fix the underlying architecture to naturally satisfy the linters.  
Maximum Type Strictness: We operate with Pyright's strict mode. No Any types unless absolutely necessary (and justified/cast at runtime). Generics and factories must be explicitly typed.  
Strict Dependency Enforcement: We use import-linter (contracts) to mechanically guarantee that jitsu.models never imports from jitsu.server or jitsu.providers.  
Protocol Safety (MCP stdio): Because the IDE agent communicates with Jitsu via JSON-RPC over stdout, we never print standard logs to stdout. All CLI outputs (typer.secho, etc.) must explicitly use err=True (routing to stderr) to prevent protocol corruption.  
No "Boilerplate Slop": Every piece of code written is drop-in and production-ready. We do not write pseudo-code or use "here is how you might do it" structures.
