# V2 Audit Report: `src/jitsu/cli`

> **Generated:** 2026-03-13 17:09:58 UTC

## 1. Dead Code Analysis (Vulture)

```text
src/jitsu/cli/main.py:30: unused function 'main_callback' (60% confidence)
src/jitsu/cli/main.py:35: unused function 'serve' (60% confidence)
src/jitsu/cli/main.py:121: unused function 'init' (60% confidence)
src/jitsu/cli/main.py:184: unused function 'submit' (60% confidence)
src/jitsu/cli/main.py:216: unused function 'queue_ls' (60% confidence)
src/jitsu/cli/main.py:223: unused function 'queue_clear' (60% confidence)
src/jitsu/cli/main.py:234: unused function 'plan' (60% confidence)
src/jitsu/cli/main.py:338: unused function 'auto' (60% confidence)
```

## 2. Cognitive Complexity (Complexipy)

```text
────────────────────────────────────────────────────────────────── 🐙 complexipy ───────────────────────────────────────────────────────────────────
cli/main.py
    main 0 PASSED
    main_callback 0 PASSED
    queue_ls 0 PASSED
    resume 0 PASSED
    run 1 PASSED
    queue_clear 2 PASSED
    auto 4 PASSED
    submit 4 PASSED
    plan 5 PASSED
    serve 8 PASSED
    init 9 PASSED

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

- **src/jitsu/cli/main.py:339** ` def auto(  # noqa: PLR0913 `

---

*End of automated report.*
