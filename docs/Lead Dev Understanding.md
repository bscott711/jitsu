# Jitsu: Project Understanding & Architecture

As the lead dev, here is my explicit understanding of our system, architecture, and the strict rules we are operating under.

## The Core Mission

We are building an inversion of control for AI agents (Antigravity, Cursor, Windsurf). Currently, agents suffer from "Context Drift"—they rely on static .md files that immediately become outdated as the codebase changes, leading to hallucinations and infinite error loops.
Jitsu solves this by forcing the agent to connect via the Model Context Protocol (MCP) and ask for its next phase. We dynamically compile the "ground truth" of the codebase (AST, schemas, exact file states) and serve it Just-In-Time (JIT) directly into the agent's context window.

## Architectural Layers (Strict Domain-Driven Design)

We enforce a one-way dependency flow to ensure the system remains perfectly decoupled:

Layer 0 - The Directive Engine (jitsu.models): Pure, strict Pydantic V2 schemas (AgentDirective, PhaseReport, ContextTarget). This is our core domain. It knows nothing about the outside world. Immutability (frozen=True) and strict typing are mandatory.

Layer 1 - Core & State (jitsu.core): The ContextCompiler and JitsuStateManager. This orchestrates the queue and weaves the directives together with the provider data into optimized Markdown.

Layer 2 - The Providers (jitsu.providers): The adapters that inspect the real world. FileStateProvider, AST dumpers, Pydantic schema extractors, Markdown structural parsers, Git analyzers, and EnvVar readers. This layer MUST be AST-First to strip noise out of the LLM context.

Layer 3 - The Transport Layer (jitsu.server & jitsu.cli): The Typer CLI, background IPC daemon, and the MCP stdio server. It translates the external world into our core domain. Progressive Disclosure via dynamically responding to `jitsu_request_context` requests is handled here.

## Coding Rules & Engineering Standards

To keep this project rock solid, we adhere strictly to the following rules:

100% Test Coverage: Mandatory. We do not merge or finalize features if coverage drops below 100%, including edge cases and hidden exception pathways.

Maximum Type Strictness: We operate with Pyright's strict mode. No Any types unless absolutely necessary (and justified). Generics and factories must be explicitly typed.

Strict Dependency Enforcement: We use import-linter (contracts) to mechanically guarantee that jitsu.models never imports from jitsu.server or jitsu.providers.

Protocol Safety (MCP stdio): Because the IDE agent communicates with Jitsu via JSON-RPC over stdout, we never print standard logs to stdout. All CLI outputs (typer.secho, etc.) must explicitly use err=True (routing to stderr) to prevent protocol corruption.

No "Boilerplate Slop": Every piece of code written is drop-in and production-ready. We do not write pseudo-code or use "here is how you might do it" structures.
