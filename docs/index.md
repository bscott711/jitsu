# **Jitsu (実) Wiki**

Welcome to the **Jitsu** documentation. Jitsu (Japanese for "Truth" or "Substance") is an **AST-first, strictly-typed AI orchestrator** designed to eliminate "Prompt Debt" and "Context Drift" in AI-capable IDEs.

## Our Mission

Jitsu enables AI agents to transition from passive code generators to **self-orchestrating collaborators**. By shifting the workload of context preparation to a high-performance Python engine, Jitsu serves the absolute "ground truth" of your codebase **Just-In-Time (JIT)**.

Key pillars of our mission:

- **Preventing Context Drift**: Using Progressive Disclosure to pull context on-demand.
- **AST-First Intelligence**: Prioritizing structural skeletons over raw source to save up to 90% of tokens.
- **Strict Orchestration**: Delivering instructions as validated Pydantic models with explicit Definitions of Done.

---

## 4-Layer Architecture

Jitsu is built on a robust, layered foundation to ensure high fidelity and autonomous execution:

### [Layer 1: The Core (Models)](Jitsu%20Architecture%20Overview.md#layer-1-strict-pydantic-models-the-core)

Rigorous Pydantic models defining the communication protocol between the orchestrator and the agent.

### [Layer 1.5: The Engine (Core & State)](Jitsu%20Architecture%20Overview.md#layer-15-core--state-the-engine)

The logic layer that parses directives, manages task lifecycles, and compiles JIT context manifests.

### [Layer 2: The Eyes (AST Providers)](Jitsu%20Architecture%20Overview.md#layer-2-ast-first-providers-the-eyes)

Specialized providers that extract structural skeletons (AST), JSON schemas, and directory trees from the filesystem.

### [Layer 3: The Transport (MCP Server)](Jitsu%20Architecture%20Overview.md#layer-3-self-orchestrating-mcp-server-the-transport-layer)

The self-orchestrating MCP server and CLI that exposes Jitsu tools to IDEs like Antigravity, Cursor, and Windsurf.

---

## Table of Contents

- [**Architecture Overview**](Jitsu%20Architecture%20Overview.md): Deep dive into the 1.0 design and autonomous loop.
- [**CLI Command Reference**](CLI%20Reference.md): Guide to `init`, `serve`, `submit`, and `queue` commands.
- [**MCP Tools Reference**](MCP%20Tools%20Reference.md): Documentation for the 8 default tools shipped with the Jitsu orchestrator.
- [**Lead Dev Understanding**](Lead%20Dev%20Understanding.md): High-level concepts for project leads.
- [**Module Audit**](module_audit/index.md): Automated architecture and dependency audits.

---

## Getting Started

To install Jitsu and start your first self-orchestrated epic, see the [README](../README.md#installation).
