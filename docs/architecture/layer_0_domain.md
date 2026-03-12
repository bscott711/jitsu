# **Layer 0: Domain Models**

Layer 0 represents the fundamental "contract" of the Jitsu system. It contains zero-dependency, strictly-typed Pydantic V2 models that define how the orchestrator and AI agents communicate.

## **Why Layer 0 is Isolated**

The Domain layer is kept strictly isolated from the rest of the application (Core, Providers, Server) for several critical reasons:

1. **Contractual Integrity**: As the "source of truth" for the IPC protocol, these models must remain stable. Isolation prevents implementation details from leaking back into the core definitions.
2. **Zero-Dependency Policy**: By avoiding external dependencies (other than Pydantic), Layer 0 ensures that changes in providers or transport layers cannot break the basic data structures.
3. **Portability**: These models can be easily shared or mirrored in other environments (like the MCP client side) without bringing along the entire Jitsu engine.
4. **Deterministic Serialization**: Pydantic V2 ensures that `AgentDirective` and `PhaseReport` objects are always serialized/deserialized consistently, preventing "Schema Drift."

---

## **Key Models**

### **`AgentDirective`**

The primary payload sent to an AI agent. It encapsulates a single atomic work phase.

- **Goal**: Defines what needs to be done.
- **Module Scope**: Specifies the files or directories relevant to the task.
- **Instructions**: Detailed markdown-based steps.
- **Anti-Patterns**: Strictly forbidden actions to prevent common agent pitfalls.
- **Context Targets**: A manifest of files the agent should pull to complete the task.
- **Definition of Done**: Clear completion criteria and verification commands.

### **`PhaseReport`**

The structured feedback submitted by the agent upon completion of a phase.

- **Status**: `SUCCESS`, `FAILED`, or `STUCK`.
- **Artifacts**: A list of files created or modified.
- **Verification Output**: Results from running required verification commands (e.g., `just verify`).
- **Agent Notes**: Qualitative feedback or reasoning for the next phase.

### **Supporting Types**

- **`TargetResolutionMode`**: Controls how the `ContextCompiler` resolves a file (e.g., `AST`, `SCHEMA`, `FULL_SOURCE`).
- **`PhaseStatus`**: Enum capturing the lifecycle of a phase.
- **`EpicBlueprint`**: A collection of directives forming a larger project goal.
