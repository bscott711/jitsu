# V2 Audit Report: `src/jitsu/core`

>
> **Generated:** 2026-03-12 06:06:38 UTC

## 1. Dead Code Analysis (Vulture)

```text
src/jitsu/core/orchestrator.py:153: unused method 'execute_run' (60% confidence)
src/jitsu/core/orchestrator.py:207: unused method 'execute_auto' (60% confidence)
src/jitsu/core/runner.py:47: unused method 'run_args' (60% confidence)
src/jitsu/core/state.py:15: unused method 'queue_directive' (60% confidence)
src/jitsu/core/state.py:26: unused method 'get_next_directive' (60% confidence)
src/jitsu/core/state.py:38: unused method 'update_phase_status' (60% confidence)
src/jitsu/core/state.py:52: unused method 'get_remaining_count' (60% confidence)
src/jitsu/core/state.py:65: unused method 'get_pending_phases' (60% confidence)
src/jitsu/core/state.py:75: unused method 'clear_queue' (60% confidence)
src/jitsu/core/state.py:80: unused property 'pending_count' (60% confidence)
src/jitsu/core/state.py:91: unused property 'completed_reports' (60% confidence)
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
    ContextCompiler::_resolve_explicit 3 PASSED
    ContextCompiler::_build_preamble 4 PASSED
    ContextCompiler::compile_directive 4 PASSED
    ContextCompiler::_resolve_targets 9 PASSED
    ContextCompiler::_resolve_auto 12 PASSED

core/executor.py
    JitsuExecutor::_apply_edits 1 PASSED
    JitsuExecutor::__init__ 2 PASSED
    JitsuExecutor::_run_verification 4 PASSED
    JitsuExecutor::execute_directive 9 PASSED

core/orchestrator.py
    JitsuOrchestrator::execute_plan 0 PASSED
    JitsuOrchestrator::finalize 0 PASSED
    JitsuOrchestrator::run_autonomous 0 PASSED
    JitsuOrchestrator::__init__ 2 PASSED
    JitsuOrchestrator::_send_payload 2 PASSED
    JitsuOrchestrator::execute_run 4 PASSED
    JitsuOrchestrator::execute_auto 8 PASSED
    JitsuOrchestrator::execute_phases 8 PASSED
    JitsuOrchestrator::run_plan 11 PASSED
    JitsuOrchestrator::_handle_planner_error 14 PASSED

core/planner.py
    JitsuPlanner::__init__ 0 PASSED
    JitsuPlanner::save_plan 0 PASSED
    JitsuPlanner::generate_plan 11 PASSED

core/runner.py
    CommandRunner::run 1 PASSED
    CommandRunner::run_args 1 PASSED

core/state.py
    JitsuStateManager::__init__ 0 PASSED
    JitsuStateManager::clear_queue 0 PASSED
    JitsuStateManager::completed_reports 0 PASSED
    JitsuStateManager::get_pending_phases 0 PASSED
    JitsuStateManager::get_remaining_count 0 PASSED
    JitsuStateManager::pending_count 0 PASSED
    JitsuStateManager::queue_directive 0 PASSED
    JitsuStateManager::update_phase_status 0 PASSED
    JitsuStateManager::get_next_directive 1 PASSED

core/storage.py
    EpicStorage::archive 0 PASSED
    EpicStorage::completed_dir 0 PASSED
    EpicStorage::completed_rel 0 PASSED
    EpicStorage::current_dir 0 PASSED
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

- **src/jitsu/core/orchestrator.py:113** ` except Exception as e:  # noqa: BLE001 `

---

*End of automated report.*
