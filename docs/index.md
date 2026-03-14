# **Jitsu**

Welcome to the **Jitsu** documentation. Jitsu is a **JIT Context & Workflow Orchestrator** designed to eliminate "Prompt Debt" and "Context Drift" in AI-capable IDEs.

## Our Mission

Jitsu enables AI agents to transition from passive code generators to **self-orchestrating collaborators**. By shifting the workload of context preparation to a high-performance Python engine, Jitsu serves the absolute "ground truth" of your codebase **Just-In-Time (JIT)**.

Key pillars of our mission:

- **Preventing Context Drift**: Using Progressive Disclosure to pull context on-demand.
- **AST-First Intelligence**: Prioritizing structural skeletons over raw source to save up to 90% of tokens.
- **Strict Orchestration**: Delivering instructions as validated Pydantic models with explicit Definitions of Done.
- **Self-Documenting Workflow**: Ensuring documentation always reflects the ground truth of the codebase automatically.

---

## 4-Layer Architecture

Jitsu is built on a robust, layered foundation to ensure high fidelity and reliable orchestration:

### [Layer 0: The Domain (Models)](architecture/layer_0_domain.md)

Rigorous Pydantic models defining the communication protocol between the orchestrator and the agent.

### [Layer 1: The Engine (Core & State)](architecture/layer_1_core.md)

The logic layer that parses directives, manages task lifecycles, and compiles JIT context manifests.

### [Layer 2: The Eyes (AST Providers)](architecture/layer_2_providers.md)

Specialized providers that extract structural skeletons (AST), JSON schemas, and directory trees from the filesystem.

### [Layer 3: The Transport (MCP Server)](architecture/layer_3_transport.md)

The MCP server and CLI that exposes Jitsu tools to IDEs like Antigravity, Cursor, and Windsurf via stdio.

---

## Table of Contents

- [**Architecture Overview**](Jitsu%20Architecture%20Overview.md): Deep dive into the design and workflow.
- [**Ecosystem Landscape & SOTA**](architecture/landscape.md): Comparative analysis vs. SOTA agents.
- [**CLI Command Reference**](CLI%20Reference.md): Guide to the `serve` command.
- [**MCP Tools Reference**](MCP%20Tools%20Reference.md): Documentation for the 9 core tools.

---

## Getting Started

To install Jitsu and start your first self-orchestrated epic, see the [README](../README.md#installation).
