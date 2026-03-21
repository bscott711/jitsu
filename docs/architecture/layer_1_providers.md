# **Layer 1: AST-First Providers**

> **Automatic Documentation Guarantee:** This documentation is automatically synchronized by Jitsu's self-documenting workflow as part of its core process.

Layer 1 is responsible for "observing" the codebase. It consists of specialized Context Providers that translate raw filesystem data into LLM-optimized representations.

---

## **The AST-First Philosophy**

The core differentiator of Layer 1 is its **AST-First** parsing policy. Most AI tools provide full source code, which includes implementation details that act as "noise" for high-level reasoning. Jitsu prioritizes structural skeletons:

- **Signatures & Docstrings**: Provides the "what" and "how" of a function/class.
- **Contract Clarity**: Stripping implementation logic saves **70-90% of tokens**, allowing agents to "see" more of the codebase simultaneously.
- **Focus**: Prevents agents from getting bogged down in implementation details when they only need to understand an API surface.

---

## **Key Components**

### **`ProviderRegistry`**

The `ProviderRegistry` allows for the dynamic registration and discovery of context providers. This extensibility allows Jitsu to support various file types and analysis strategies (e.g., Python AST, JSON Schema, Git Status, Directory Trees).

- **Discovery**: The `ContextCompiler` queries the registry to find the best provider for a given `TargetResolutionMode`.
- **Extensibility**: New providers (like a SQL Schema provider or a Dockerfile analyzer) can be added without modifying the core compiler logic.

### **Types of Providers**

Jitsu utilizes 10 core tool components to resolve context:

- **AST Provider (`ast`)**: The primary provider for Python files. Uses the `ast` module to extract structural information.
- **Pydantic Provider (`pydantic`)**: Uses live reflection to generate JSON schemas from Pydantic models.
- **FileState Provider (`file`)**: A raw-text fallback when full implementation is required.
- **Git Provider (`git`)**: Integrates live repository state (diffs, status) into the context.
- **Tree Provider (`tree`)**: Generates visual directory structures for navigational context.
- **Markdown AST Provider (`markdown_ast`)**: Extracts headings and code blocks from large markdown files.
- **Env Var Provider (`env_var`)**: Safely exposes necessary environment configurations.
- **Base Metadata**: Provides the foundation for all provider implementations.
- **Provider Registry**: The central discovery mechanism for context resolution.
- **Context Compiler**: Orchestrates providers to generate JIT prompt manifests.

---

## **Provider Lifecycle**

1. **Initialization**: Providers are initialized with the workspace root to ensure all paths are absolute and sandboxed.
2. **Resolution**: The `resolve(target)` method is called with a specific identifier (module name, file path, or class name).
