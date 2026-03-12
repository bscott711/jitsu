# V2 Audit Report: `src/jitsu/cli`

> **Generated:** 2026-03-12 19:58:33 UTC

## 1. Dead Code Analysis (Vulture)

```text
src/jitsu/cli/main.py:29: unused function 'main_callback' (60% confidence)
src/jitsu/cli/main.py:34: unused function 'serve' (60% confidence)
src/jitsu/cli/main.py:120: unused function 'init' (60% confidence)
src/jitsu/cli/main.py:183: unused function 'submit' (60% confidence)
src/jitsu/cli/main.py:215: unused function 'queue_ls' (60% confidence)
src/jitsu/cli/main.py:222: unused function 'queue_clear' (60% confidence)
src/jitsu/cli/main.py:233: unused function 'plan' (60% confidence)
src/jitsu/cli/main.py:322: unused function 'auto' (60% confidence)
```

## 2. Cognitive Complexity (Complexipy)

```text
───────────── 🐙 complexipy ─────────────
cli/main.py
    main 0 PASSED
    main_callback 0 PASSED
    queue_ls 0 PASSED
    run 1 PASSED
    auto 2 PASSED
    plan 2 PASSED
    queue_clear 2 PASSED
    submit 4 PASSED
    serve 8 PASSED
    init 9 PASSED

All functions are within the allowed 
complexity.
─────── 🎉 Analysis completed! 🎉 ───────
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
