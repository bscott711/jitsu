# V2 Audit Report: `src/jitsu/core`

> **Generated:** 2026-03-12 19:58:33 UTC

## 1. Dead Code Analysis (Vulture)

```text
src/jitsu/core/orchestrator.py:156: unused method 'execute_run' (60% confidence)
src/jitsu/core/orchestrator.py:210: unused method 'execute_auto' (60% confidence)
src/jitsu/core/runner.py:47: unused method 'run_args' (60% confidence)
src/jitsu/core/state.py:15: unused method 'queue_directive' (60% confidence)
src/jitsu/core/state.py:26: unused method 'get_next_directive' (60% confidence)
src/jitsu/core/state.py:65: unused method 'on_stuck' (60% confidence)
src/jitsu/core/state.py:76: unused method 'get_remaining_count' (60% confidence)
src/jitsu/core/state.py:89: unused method 'get_pending_phases' (60% confidence)
src/jitsu/core/state.py:104: unused property 'pending_count' (60% confidence)
src/jitsu/core/state.py:115: unused property 'completed_reports' (60% confidence)
```

## 2. Cognitive Complexity (Complexipy)

```text
───────────── 🐙 complexipy ─────────────
core/client.py
    LLMClientFactory::create 1 PASSED

core/compiler.py
    ContextCompiler::_get_manifest_summar
y 0 PASSED
    ContextCompiler::__init__ 1 PASSED
    ContextCompiler::_try_resolve 2 
PASSED
    ContextCompiler::compile_directive 3 
PASSED
    ContextCompiler::resolve_explicit 3 
PASSED
    ContextCompiler::_build_preamble 4 
PASSED
    ContextCompiler::_resolve_targets 9 
PASSED
    ContextCompiler::resolve_auto 12 
PASSED

core/executor.py
    JitsuExecutor::_apply_edits 1 PASSED
    JitsuExecutor::_check_monotonicity 2 
PASSED
    JitsuExecutor::__init__ 3 PASSED
    JitsuExecutor::parse_failure_count 3 
PASSED
    JitsuExecutor::run_verification 3 
PASSED
    JitsuExecutor::enforce_scope 6 PASSED
    JitsuExecutor::_augment_recovery_mess
age 8 PASSED
    JitsuExecutor::extract_first_failure_
block 9 PASSED
    JitsuExecutor::execute_directive 14 
PASSED

core/orchestrator.py
    JitsuOrchestrator::execute_plan 0 
PASSED
    JitsuOrchestrator::finalize 0 PASSED
    JitsuOrchestrator::run_autonomous 0 
PASSED
    JitsuOrchestrator::send_payload 2 
PASSED
    JitsuOrchestrator::__init__ 3 PASSED
    JitsuOrchestrator::execute_run 4 
PASSED
    JitsuOrchestrator::execute_auto 8 
PASSED
    JitsuOrchestrator::run_plan 11 PASSED
    JitsuOrchestrator::handle_planner_err
or 14 PASSED
    JitsuOrchestrator::execute_phases 15 
PASSED

core/planner.py
    JitsuPlanner::__init__ 0 PASSED
    JitsuPlanner::save_plan 0 PASSED
    JitsuPlanner::generate_plan 9 PASSED

core/runner.py
    CommandRunner::run 1 PASSED
    CommandRunner::run_args 1 PASSED

core/state.py
    JitsuStateManager::__init__ 0 PASSED
    JitsuStateManager::clear_queue 0 
PASSED
    JitsuStateManager::completed_reports 
0 PASSED
    JitsuStateManager::get_pending_phases
0 PASSED
    JitsuStateManager::get_remaining_coun
t 0 PASSED
    JitsuStateManager::on_stuck 0 PASSED
    JitsuStateManager::pending_count 0 
PASSED
    JitsuStateManager::queue_directive 0 
PASSED
    JitsuStateManager::update_phase 0 
PASSED
    JitsuStateManager::update_phase_statu
s 0 PASSED
    JitsuStateManager::get_next_directive
1 PASSED

core/storage.py
    EpicStorage::archive 0 PASSED
    EpicStorage::completed_dir 0 PASSED
    EpicStorage::completed_rel 0 PASSED
    EpicStorage::current_dir 0 PASSED
    EpicStorage::read_bytes 0 PASSED
    EpicStorage::read_text 0 PASSED
    EpicStorage::rel_path 0 PASSED
    EpicStorage::__init__ 1 PASSED

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
