# V2 Audit Report: `src/jitsu/core`

> **Generated:** 2026-03-13 17:09:58 UTC

## 1. Dead Code Analysis (Vulture)

```text
src/jitsu/core/orchestrator.py:185: unused method 'execute_run' (60% confidence)
src/jitsu/core/orchestrator.py:253: unused method 'execute_auto' (60% confidence)
src/jitsu/core/orchestrator.py:517: unused method 'resume' (60% confidence)
src/jitsu/core/runner.py:47: unused method 'run_args' (60% confidence)
src/jitsu/core/state.py:21: unused method 'queue_directive' (60% confidence)
src/jitsu/core/state.py:32: unused method 'get_next_directive' (60% confidence)
src/jitsu/core/state.py:71: unused method 'on_stuck' (60% confidence)
src/jitsu/core/state.py:82: unused method 'get_remaining_count' (60% confidence)
src/jitsu/core/state.py:95: unused method 'get_pending_phases' (60% confidence)
src/jitsu/core/state.py:110: unused property 'pending_count' (60% confidence)
src/jitsu/core/state.py:121: unused property 'completed_reports' (60% confidence)
```

## 2. Cognitive Complexity (Complexipy)

```text
────────────────────────────────────────────────────────────────── 🐙 complexipy ───────────────────────────────────────────────────────────────────
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

core/executor.py
    JitsuExecutor::_handle_attempt_failure 0 PASSED
    JitsuExecutor::_apply_edits 1 PASSED
    JitsuExecutor::_check_monotonicity 2 PASSED
    JitsuExecutor::_execute_tool 2 PASSED
    JitsuExecutor::_report_api_issue 2 PASSED
    JitsuExecutor::_run_react_loop 3 PASSED
    JitsuExecutor::parse_failure_count 3 PASSED
    JitsuExecutor::run_verification 3 PASSED
    JitsuExecutor::__init__ 4 PASSED
    JitsuExecutor::execute_directive 5 PASSED
    JitsuExecutor::enforce_scope 6 PASSED
    JitsuExecutor::extract_first_failure_block 9 PASSED
    JitsuExecutor::_execute_attempt_cycle 11 PASSED
    JitsuExecutor::augment_recovery_message 14 PASSED

core/orchestrator.py
    JitsuOrchestrator::execute_plan 0 PASSED
    JitsuOrchestrator::finish 2 PASSED
    JitsuOrchestrator::run_autonomous 2 PASSED
    JitsuOrchestrator::send_payload 2 PASSED
    JitsuOrchestrator::__init__ 3 PASSED
    JitsuOrchestrator::execute_run 4 PASSED
    JitsuOrchestrator::_handle_quarantine 5 PASSED
    JitsuOrchestrator::execute_auto 8 PASSED
    JitsuOrchestrator::run_plan 11 PASSED
    JitsuOrchestrator::handle_planner_error 14 PASSED
    JitsuOrchestrator::resume 14 PASSED
    JitsuOrchestrator::execute_phases 15 PASSED

core/planner.py
    JitsuPlanner::__init__ 0 PASSED
    JitsuPlanner::save_plan 0 PASSED
    JitsuPlanner::compile_phases 5 PASSED
    JitsuPlanner::generate_plan 10 PASSED

core/runner.py
    CommandRunner::run 1 PASSED
    CommandRunner::run_args 1 PASSED

core/state.py
    JitsuStateManager::clear_queue 0 PASSED
    JitsuStateManager::completed_reports 0 PASSED
    JitsuStateManager::get_pending_phases 0 PASSED
    JitsuStateManager::get_remaining_count 0 PASSED
    JitsuStateManager::on_stuck 0 PASSED
    JitsuStateManager::pending_count 0 PASSED
    JitsuStateManager::queue_directive 0 PASSED
    JitsuStateManager::update_phase 0 PASSED
    JitsuStateManager::update_phase_status 0 PASSED
    JitsuStateManager::__init__ 1 PASSED
    JitsuStateManager::get_next_directive 1 PASSED
    JitsuStateManager::hydrate_for_resume 7 PASSED

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

- **src/jitsu/core/orchestrator.py:62** ` async def run_plan(  # noqa: PLR0913 `
- **src/jitsu/core/orchestrator.py:145** ` async def execute_plan(  # noqa: PLR0913 `
- **src/jitsu/core/orchestrator.py:185** ` async def execute_run(  # noqa: PLR0913 `
- **src/jitsu/core/orchestrator.py:253** ` async def execute_auto(  # noqa: PLR0913 `

---

*End of automated report.*
