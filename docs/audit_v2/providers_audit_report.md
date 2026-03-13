# V2 Audit Report: `src/jitsu/providers`

> **Generated:** 2026-03-13 17:09:58 UTC

## 1. Dead Code Analysis (Vulture)

```text
src/jitsu/providers/ast.py:61: unused method 'resolve' (60% confidence)
src/jitsu/providers/base.py:39: unused method 'resolve' (60% confidence)
src/jitsu/providers/env.py:16: unused method 'resolve' (60% confidence)
src/jitsu/providers/file.py:14: unused method 'resolve' (60% confidence)
src/jitsu/providers/git.py:76: unused method 'resolve' (60% confidence)
src/jitsu/providers/git.py:104: unused method 'get_current_branch' (60% confidence)
src/jitsu/providers/git.py:117: unused method 'create_and_checkout_branch' (60% confidence)
src/jitsu/providers/git.py:143: unused method 'merge_branch' (60% confidence)
src/jitsu/providers/git.py:158: unused method 'delete_branch' (60% confidence)
src/jitsu/providers/markdown.py:57: unused method 'resolve' (60% confidence)
src/jitsu/providers/pydantic.py:23: unused method 'resolve' (60% confidence)
src/jitsu/providers/tree.py:32: unused method 'resolve' (60% confidence)
```

## 2. Cognitive Complexity (Complexipy)

```text
────────────────────────────────────────────────────────────────── 🐙 complexipy ───────────────────────────────────────────────────────────────────
providers/ast.py
    ASTProvider::name 0 PASSED
    ASTProvider::_format_function_def 3 PASSED
    ASTProvider::_format_class_def 4 PASSED
    ASTProvider::resolve 8 PASSED

providers/base.py
    BaseProvider::__init__ 0 PASSED
    BaseProvider::name 0 PASSED
    BaseProvider::resolve 0 PASSED

providers/env.py
    EnvVarProvider::name 0 PASSED
    EnvVarProvider::resolve 1 PASSED

providers/file.py
    FileStateProvider::name 0 PASSED
    FileStateProvider::resolve 3 PASSED

providers/git.py
    GitProvider::checkout_branch 0 PASSED
    GitProvider::create_and_checkout_branch 0 PASSED
    GitProvider::delete_branch 0 PASSED
    GitProvider::get_current_branch 0 PASSED
    GitProvider::merge_branch 0 PASSED
    GitProvider::name 0 PASSED
    GitError::__init__ 3 PASSED
    GitProvider::_run_git 3 PASSED
    GitProvider::resolve 8 PASSED

providers/markdown.py
    MarkdownASTProvider::name 0 PASSED
    MarkdownASTProvider::read 3 PASSED
    MarkdownASTProvider::resolve 3 PASSED
    MarkdownASTProvider::_is_structural 5 PASSED

providers/pydantic.py
    PydanticProvider::name 0 PASSED
    PydanticProvider::resolve 7 PASSED

providers/tree.py
    DirectoryTreeProvider::_get_sorted_items 0 PASSED
    DirectoryTreeProvider::name 0 PASSED
    DirectoryTreeProvider::resolve 6 PASSED
    DirectoryTreeProvider::_generate_tree_lines 14 PASSED

All functions are within the allowed complexity.
──────────────────────────────────────────────────────────── 🎉 Analysis completed! 🎉 ─────────────────────────────────────────────────────────────
```

## 3. Linting (Ruff)

```text
All checks passed!
```

## 4. Static Typing (Pyright)

```text
0 errors, 0 warnings, 0 informations
```

## 5. Technical Debt (Inline Ignores)

No inline ignores found! 🎉

---

*End of automated report.*
