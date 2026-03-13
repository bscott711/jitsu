# **Jitsu Roadmap**

This document tracks the completed architectural milestones and the future vision for the Jitsu orchestrator.

## **✅ COMPLETED: The Jitsu Foundation**

### **Milestone 1: The U-Curve Compiler (Attention Management)**

- **XML Tag Standardization**: Implemented strict XML string constants for high-fidelity instruction delivery.
- **U-Curve Refactor**: Optimized context structure to place instructions at the edges of the window, solving the "Lost in the Middle" problem.
- **Token Optimization**: Built AST-first providers that save up to 90% of tokens while maintaining structural context.

### **Milestone 2: Slim Refactor (MCP Centralization)**

- **Autonomous Loop Removal**: Stripped the internal executor and orchestrator to defer execution responsibility to external AI agents (like Antigravity or Cursor).
- **Transport Simplification**: Removed the background IPC daemon; Jitsu now communicates exclusively via the Model Context Protocol (MCP) over stdio.
- **Minimalist CLI**: Reduced the CLI to a single `serve` command, focusing on a server-first architecture.

## **🚀 FUTURE: v1.0 and Beyond**

### **Milestone 3: Advanced Provider Ecosystem**

- **Database Schema Provider**: Dynamic reflection of SQL schemas for migration tasks.
- **Docker/Environment Context**: Injecting container logs and environment variables into the context window.
- **Cross-Repo Context**: Allowing Jitsu to pull state from multiple related repositories simultaneously.

### **Milestone 4: Orchestration Ergonomics**

- **Live State Inspection**: A web-based dashboard for visualizing the orchestration queue and phase reports.
- **History & Rollback**: Built-in mechanisms for reverting specifically to a previously successful phase in an epic.
- **Concurrency Support**: Enabling multiple agents to pull and report on different phases of the same epic concurrently.
