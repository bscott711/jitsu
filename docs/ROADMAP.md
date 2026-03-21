# **Jitsu Strategic Roadmap**

This roadmap outlines high-value features designed to elevate the Jitsu agentic framework by increasing developer velocity and operational robustness.

## **1. Parallel Verification Engine (Priority: Highest)**

**Goal:** Drastically reduce the time spent in the `just verify` loop for large-scale changes.

* Objective: Integrate `pytest-xdist` to parallelize test execution across multiple CPU cores.
* Velocity Impact: Drastic reduction in feedback latency during intensive refactoring cycles.
* Implementation: Update `JustFile` and `pyproject.toml` to support `pytest -n auto`.

## **2. AST-Based Auto-Refactor Toolkit**

**Goal:** Provide the agent with safe, structurally-aware code mutation tools.

* Objective: Extend the `ASTProvider` to support transformation patterns (e.g., "Rename Class," "Extract Method") that are validated against the AST before file writes.
* Velocity Impact: Reduces manual string manipulation errors and "Broken AST" loops.
* Implementation: Introduce a new `Transformer` class in `src/jitsu/providers/ast.py`.

## **3. Persistent Session Store (SQLite Backend)**

**Goal:** Ensure orchestration state survives server restarts or client disconnects.

* Objective: Migrate `JitsuStateManager` from in-memory lists to a SQLite-backed relational model.
* Velocity Impact: Allows for multi-day epics and robust recovery after crashes or IDE reloads.
* Implementation: Develop `src/jitsu/core/db.py` utilizing `aiosqlite` for asynchronous state management.

## **4. Automated Git-Backed Rollbacks**

**Goal:** Guarantee a "Clean State" after every failed phase.

* Objective: Implement middleware that creates a git checkpoint (temporary branch or commit) before a phase starts. If `just verify` fails, it automatically reverts to the checkpoint.
* Velocity Impact: Eliminates the need for manual cleanup after failed experimental phases.
* Implementation: Integrate checkpoint logic within the core execution loop in `src/jitsu/core/runner.py`.

## **5. Multi-Repo Orchestration**

**Goal:** Enable Jitsu to pull context and plan across repository boundaries.

* Objective: Support planning and executing epics that span multiple related microservices or monorepo packages.
* Velocity Impact: Enables complex system-wide refactors without manual context stitching.
* Implementation: Update `DirectoryTreeProvider` to handle a registry of workspace paths.

> [!TIP]
> **Developer Velocity First:** We prioritize features that shorten the **Plan-Execute-Verify** cycle, as this is the primary bottleneck for agentic workflows.
