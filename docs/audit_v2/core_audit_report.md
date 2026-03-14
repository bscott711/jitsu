# V2 Audit Report: `src/jitsu/core`

> **Generated:** 2026-03-14 02:25:02 UTC

## 1. Dead Code Analysis (Vulture)

```text
src/jitsu/core/compiler.py:20: unused class 'ContextCompiler' (60% confidence)
src/jitsu/core/compiler.py:87: unused method 'compile_directive' (60% confidence)
src/jitsu/core/planner.py:93: unused method 'generate_plan' (60% confidence)
src/jitsu/core/planner.py:284: unused method 'save_plan' (60% confidence)
src/jitsu/core/runner.py:8: unused class 'CommandRunner' (60% confidence)
src/jitsu/core/runner.py:47: unused method 'run_args' (60% confidence)
src/jitsu/core/state.py:15: unused method 'queue_directive' (60% confidence)
src/jitsu/core/state.py:26: unused method 'get_next_directive' (60% confidence)
src/jitsu/core/state.py:52: unused method 'on_stuck' (60% confidence)
src/jitsu/core/state.py:63: unused method 'get_remaining_count' (60% confidence)
src/jitsu/core/state.py:76: unused method 'get_pending_phases' (60% confidence)
src/jitsu/core/state.py:91: unused property 'pending_count' (60% confidence)
src/jitsu/core/state.py:102: unused property 'completed_reports' (60% confidence)
src/jitsu/core/storage.py:33: unused method 'get_current_path' (60% confidence)
src/jitsu/core/storage.py:84: unused method 'archive' (60% confidence)
src/jitsu/core/storage.py:115: unused method 'completed_rel' (60% confidence)
```

## 2. Cognitive Complexity (Complexipy)

```text
──────────────────────────────────────── 🐙 complexipy ────────────────────────────────────────
core/client.py
    LLMClientFactory::create 1 PASSED

core/compiler.py
    ContextCompiler::_get_manifest_summary 0 PASSED
    ContextCompiler::__init__ 1 PASSED
    ContextCompiler::_try_resolve 2 PASSED
    ContextCompiler::compile_directive 3 PASSED
    ContextCompiler::resolve_explicit 3 PASSED
    ContextCompiler::_build_preamble 4 PASSED
    ContextCompiler::_resolve_targets 9 PASSED
    ContextCompiler::resolve_auto 12 PASSED

core/planner.py
    JitsuPlanner::__init__ 0 PASSED
    JitsuPlanner::save_plan 0 PASSED
    JitsuPlanner::compile_phases 5 PASSED
    JitsuPlanner::_emit_status 7 PASSED
    JitsuPlanner::generate_plan 8 PASSED

core/runner.py
    CommandRunner::run 1 PASSED
    CommandRunner::run_args 1 PASSED

core/state.py
    JitsuStateManager::__init__ 0 PASSED
    JitsuStateManager::clear_queue 0 PASSED
    JitsuStateManager::completed_reports 0 PASSED
    JitsuStateManager::get_pending_phases 0 PASSED
    JitsuStateManager::get_remaining_count 0 PASSED
    JitsuStateManager::on_stuck 0 PASSED
    JitsuStateManager::pending_count 0 PASSED
    JitsuStateManager::queue_directive 0 PASSED
    JitsuStateManager::update_phase_status 0 PASSED
    JitsuStateManager::get_next_directive 1 PASSED

core/storage.py
    EpicStorage::archive 0 PASSED
    EpicStorage::completed_dir 0 PASSED
    EpicStorage::completed_rel 0 PASSED
    EpicStorage::current_dir 0 PASSED
    EpicStorage::get_current_path 0 PASSED
    EpicStorage::read_bytes 0 PASSED
    EpicStorage::read_text 0 PASSED
    EpicStorage::rel_path 0 PASSED
    EpicStorage::__init__ 1 PASSED

All functions are within the allowed complexity.
────────────────────────────────── 🎉 Analysis completed! 🎉 ──────────────────────────────────
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
