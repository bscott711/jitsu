# Epic 2: AST Provider Implementation Plan - Phase 01: Research & Design

## Objective

The `ASTProvider` will extract a lightweight structural outline of a Python file using the built-in `ast` module. This provides the LLM agent with the "skeleton" of a module (classes, methods, signatures, docstrings) without consuming excessive tokens with implementation details.

## Design Goals

- **Token Efficiency:** Only extract structural metadata (names, signatures, docstrings).
- **Graceful Failure:** Log syntax errors or missing files to `stderr` and return a standard markdown error message.
- **Strict Logging:** Use `jitsu.utils.logger.get_logger`.
- **Formatting:** Output as a clean Markdown block using standard Python syntax highlighting.

## Research Findings: The `ast` Module

Based on research of the Python `ast` module:

1. **Parsing:** `ast.parse(source)` will be used to generate the Abstract Syntax Tree.
2. **Traversal:** Using `ast.NodeVisitor` or `ast.walk()` is suitable, but `ast.NodeVisitor` allows for more structured hierarchical extraction.
3. **Signatures:** For Python 3.9+, `ast.unparse(node.args)` can reconstruct the signature from the `ast.arguments` node. For maximum compatibility and precision, we will reconstruct the argument string manually or rely on `ast.unparse` if available.
4. **Docstrings:** `ast.get_docstring(node)` is a reliable way to extract the top-level docstring for classes, functions, and methods.

## Proposed Structure (`src/jitsu/providers/ast.py`)

### 1. The `ASTProvider` Class

- **Name:** `"ast"`
- **Dependencies:** `ast`, `pathlib`, `jitsu.utils.logger`.

### 2. Resolution Logic

1. Validate that the target is a valid file path.
2. Read the file content safely.
3. Call `ast.parse()`.
4. Traverse the tree and extract:
    **Classes:** Name, base classes, and docstring.
    **Methods:** Name, arguments, and docstring.
    **Functions:** Name, arguments, and docstring.
5. Format the result into a nested Markdown list or a pseudo-code skeleton.

### 3. Error Handling

- **`FileNotFoundError`:** Catch, log, and return `[ERROR: File not found: <path>]`.
- **`SyntaxError`:** Catch, log, and return `[ERROR: Syntax error in <path>: <details>]`.
- **`PermissionError`:** Catch, log, and return `[ERROR: Permission denied: <path>]`.

## Next Steps

- Implement the `ASTProvider` in `src/jitsu/providers/ast.py`.
- Register it in `src/jitsu/providers/__init__.py`.
- Verify extraction with a sample file containing complex signatures and docstrings.
