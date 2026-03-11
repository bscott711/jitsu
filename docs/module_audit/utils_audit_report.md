# Utils Module Architectural Audit Report

## 1. Global State and Tight Coupling via `root()`

**Nature of Violation:** `src/jitsu/utils/path.py` defines a `root()` function that uses `__file__` to scan upwards for `pyproject.toml` and returns a cached `Path` to the project root.

- **Impact:** This function is imported globally by `ContextProviders` (like `FileStateProvider` and `MarkdownASTProvider`) to resolve target files. This creates a hidden global dependency. If a developer wanted to run Jitsu to analyze a directory outside of where Jitsu's code lives, these providers would fail because they lock onto Jitsu's own root rather than an injected working directory.
- **Fix:** Remove or limit the usage of the global `root()` function. Providers should accept a `base_dir` or `workspace_root` during instantiation or method resolution. The CLI/Server should be responsible for determining the user's intended workspace root and passing it down structurally.

## 2. Global Logger State

**Nature of Violation:** `src/jitsu/utils/logger.py` maintains a module-level `_configured_loggers: set[str]` list to keep track of configured logger instances.

- **Impact:** Modifying a global set acts as hidden state across modules. While this is primarily used as a workaround to assure MCP servers don't output random logs to `sys.stdout`, it could lead to unexpected behavior during testing if loggers need to be reset.
- **Fix:** Consider encapsulating this setup inside a proper `LogManager` class initialized exactly once in the CLI or Server entry point, establishing the configuration at the application boundary rather than side-effecting upon module import or lazy-fetching.

## Conclusion

The `utils` module defines hidden global states that are bleeding into the domain architecture (especially providers), violating the Dependency Inversion Principle. Extracting these into instantiated config objects passed from the root orchestrators will clean up these tight dependencies.
