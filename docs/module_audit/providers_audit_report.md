# Providers Module Architectural Audit Report

## 1. Tight Coupling to Host System Environment

**Nature of Violation:** `src/jitsu/providers/git.py` directly executes `subprocess.run` with a hardcoded binary path `"/usr/bin/git"`.

- **Impact:** This tightly couples the provider to Unix-like systems where git is installed specifically at `/usr/local/bin` or `/usr/bin`. This will fail on Windows or custom environments, violating the Dependency Inversion Principle.
- **Fix:** Use `shutil.which("git")` to dynamically locate the binary, or abstract command execution so that the provider does not directly interface with `subprocess.run`.

## 2. Tight Coupling to Global Context (root)

**Nature of Violation:** `src/jitsu/providers/file.py`, `src/jitsu/providers/markdown.py`, and others directly import and call `from jitsu.utils import root` to resolve their target paths.

- **Impact:** Providers are inextricably linked to the globally defined project root. This makes it impossible to use them to parse files outside of the Jitsu project directory or dynamically change the root during runtime or testing.
- **Fix:** `BaseProvider` should accept a `working_directory` or `root_path` during its initialization (`__init__`), or the `resolve()` signature should accept a base path, allowing true dependency injection.

## 3. Blind Exception Catching (`# noqa: BLE001`)

**Nature of Violation:** Multiple providers silence the linter and blindly catch all `Exception`s.

- **`src/jitsu/providers/file.py`:** Line 27 catches `Exception` during `target_path.read_text()`.
- **`src/jitsu/providers/markdown.py`:** Line 52 catches `Exception` during file iteration.
- **`src/jitsu/providers/tree.py`:** Catches `Exception` multiple times during tree traversal.
- **Impact:** Masking all exceptions makes debugging very difficult. It can obscure `UnicodeDecodeError`, `PermissionError`, or OS-level faults that the calling function might need to know about to report to the user.
- **Fix:** Catch specific anticipated exceptions like `OSError` or `UnicodeDecodeError`, and let others bubble up or log the stack trace using `logger.exception`.

## Recommended Structural Fixes

1. **Refactor `BaseProvider` Init:** Add `def __init__(self, root_path: Path):` to the abstract base class and require all subclass providers to use the injected path rather than a global getter.
2. **Remove Binary Hardcoding:** Update `git.py` to use `shutil.which` or inject a `CommandRunner` dependency.
3. **Strict Error Handling:** Remove `# noqa: BLE001` occurrences by specifying exactly which IOError or Parsing exceptions should be swallowed.
