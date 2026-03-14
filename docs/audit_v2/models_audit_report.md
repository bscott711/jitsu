# V2 Audit Report: `src/jitsu/models`

> **Generated:** 2026-03-14 02:25:02 UTC

## 1. Dead Code Analysis (Vulture)

```text
src/jitsu/models/core.py:22: unused variable 'PENDING' (60% confidence)
src/jitsu/models/core.py:23: unused variable 'RUNNING' (60% confidence)
src/jitsu/models/core.py:24: unused variable 'SUCCESS' (60% confidence)
src/jitsu/models/core.py:25: unused variable 'FAILED' (60% confidence)
src/jitsu/models/core.py:26: unused variable 'STUCK' (60% confidence)
src/jitsu/models/core.py:33: unused variable 'STRUCTURE_ONLY' (60% confidence)
src/jitsu/models/core.py:34: unused variable 'FULL_SOURCE' (60% confidence)
src/jitsu/models/core.py:35: unused variable 'SCHEMA_ONLY' (60% confidence)
src/jitsu/models/core.py:41: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:43: unused variable 'include' (60% confidence)
src/jitsu/models/core.py:44: unused variable 'exclude' (60% confidence)
src/jitsu/models/core.py:50: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:52: unused variable 'phase_id' (60% confidence)
src/jitsu/models/core.py:53: unused variable 'description' (60% confidence)
src/jitsu/models/core.py:56: unused class 'EpicBlueprint' (60% confidence)
src/jitsu/models/core.py:59: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:61: unused variable 'epic_id' (60% confidence)
src/jitsu/models/core.py:64: unused method 'validate_phases_not_empty' (60% confidence)
src/jitsu/models/core.py:76: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:78: unused variable 'provider_name' (60% confidence)
src/jitsu/models/core.py:82: unused variable 'target_identifier' (60% confidence)
src/jitsu/models/core.py:86: unused variable 'is_required' (60% confidence)
src/jitsu/models/core.py:87: unused variable 'resolution_mode' (60% confidence)
src/jitsu/models/core.py:89: unused method 'validate_provider_name' (60% confidence)
src/jitsu/models/core.py:91: unused variable 'cls' (100% confidence)
src/jitsu/models/core.py:102: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:104: unused variable 'epic_id' (60% confidence)
src/jitsu/models/core.py:105: unused variable 'phase_id' (60% confidence)
src/jitsu/models/core.py:107: unused variable 'instructions' (60% confidence)
src/jitsu/models/core.py:108: unused variable 'context_targets' (60% confidence)
src/jitsu/models/core.py:109: unused variable 'anti_patterns' (60% confidence)
src/jitsu/models/core.py:110: unused variable 'verification_commands' (60% confidence)
src/jitsu/models/core.py:114: unused variable 'completion_criteria' (60% confidence)
src/jitsu/models/core.py:115: unused variable 'context_injection' (60% confidence)
src/jitsu/models/core.py:117: unused method 'validate_module_scope_not_empty' (60% confidence)
src/jitsu/models/core.py:125: unused method 'enforce_zero_bypass_verification' (60% confidence)
src/jitsu/models/core.py:127: unused variable 'cls' (100% confidence)
src/jitsu/models/core.py:138: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:140: unused variable 'phase_id' (60% confidence)
src/jitsu/models/core.py:141: unused variable 'status' (60% confidence)
src/jitsu/models/core.py:142: unused variable 'artifacts_generated' (60% confidence)
src/jitsu/models/core.py:143: unused variable 'agent_notes' (60% confidence)
src/jitsu/models/core.py:144: unused variable 'verification_output' (60% confidence)
src/jitsu/models/execution.py:14: unused variable 'INITIALIZING' (60% confidence)
src/jitsu/models/execution.py:15: unused variable 'ANALYZING_SCOPE' (60% confidence)
src/jitsu/models/execution.py:16: unused variable 'DRAFTING_PHASES' (60% confidence)
src/jitsu/models/execution.py:17: unused variable 'VALIDATING_SCHEMA' (60% confidence)
src/jitsu/models/execution.py:18: unused variable 'COMPLETE' (60% confidence)
src/jitsu/models/execution.py:24: unused variable 'model_config' (60% confidence)
src/jitsu/models/execution.py:26: unused variable 'timestamp' (60% confidence)
src/jitsu/models/execution.py:27: unused variable 'stage' (60% confidence)
src/jitsu/models/execution.py:28: unused variable 'message' (60% confidence)
src/jitsu/models/execution.py:29: unused variable 'progress_percent' (60% confidence)
src/jitsu/models/execution.py:36: unused variable 'update' (100% confidence)
src/jitsu/models/execution.py:41: unused class 'PlannerOptions' (60% confidence)
src/jitsu/models/execution.py:44: unused variable 'model_config' (60% confidence)
src/jitsu/models/execution.py:46: unused variable 'model' (60% confidence)
src/jitsu/models/execution.py:47: unused variable 'verbose' (60% confidence)
src/jitsu/models/execution.py:48: unused variable 'include_paths' (60% confidence)
src/jitsu/models/execution.py:49: unused variable 'exclude_paths' (60% confidence)
src/jitsu/models/execution.py:50: unused variable 'on_progress' (60% confidence)
src/jitsu/models/execution.py:51: unused variable 'on_status' (60% confidence)
```

## 2. Cognitive Complexity (Complexipy)

```text
──────────────────────────────────────── 🐙 complexipy ────────────────────────────────────────
models/core.py
    AgentDirective::enforce_zero_bypass_verification 1 PASSED
    ContextTarget::validate_provider_name 1 PASSED
    EpicBlueprint::validate_phases_not_empty 1 PASSED
    AgentDirective::validate_module_scope_not_empty 2 PASSED

models/execution.py
    PlannerStatusCallback::__call__ 0 PASSED

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
