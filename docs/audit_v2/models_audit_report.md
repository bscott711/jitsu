# V2 Audit Report: `src/jitsu/models`

> **Generated:** 2026-03-13 17:09:58 UTC

## 1. Dead Code Analysis (Vulture)

```text
src/jitsu/models/core.py:11: unused variable 'PENDING' (60% confidence)
src/jitsu/models/core.py:12: unused variable 'RUNNING' (60% confidence)
src/jitsu/models/core.py:13: unused variable 'SUCCESS' (60% confidence)
src/jitsu/models/core.py:14: unused variable 'FAILED' (60% confidence)
src/jitsu/models/core.py:15: unused variable 'STUCK' (60% confidence)
src/jitsu/models/core.py:22: unused variable 'STRUCTURE_ONLY' (60% confidence)
src/jitsu/models/core.py:23: unused variable 'FULL_SOURCE' (60% confidence)
src/jitsu/models/core.py:24: unused variable 'SCHEMA_ONLY' (60% confidence)
src/jitsu/models/core.py:30: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:32: unused variable 'include' (60% confidence)
src/jitsu/models/core.py:33: unused variable 'exclude' (60% confidence)
src/jitsu/models/core.py:39: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:41: unused variable 'phase_id' (60% confidence)
src/jitsu/models/core.py:42: unused variable 'description' (60% confidence)
src/jitsu/models/core.py:45: unused class 'EpicBlueprint' (60% confidence)
src/jitsu/models/core.py:48: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:50: unused variable 'epic_id' (60% confidence)
src/jitsu/models/core.py:51: unused variable 'phases' (60% confidence)
src/jitsu/models/core.py:57: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:59: unused variable 'provider_name' (60% confidence)
src/jitsu/models/core.py:63: unused variable 'target_identifier' (60% confidence)
src/jitsu/models/core.py:67: unused variable 'is_required' (60% confidence)
src/jitsu/models/core.py:68: unused variable 'resolution_mode' (60% confidence)
src/jitsu/models/core.py:74: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:76: unused variable 'epic_id' (60% confidence)
src/jitsu/models/core.py:77: unused variable 'phase_id' (60% confidence)
src/jitsu/models/core.py:78: unused variable 'module_scope' (60% confidence)
src/jitsu/models/core.py:79: unused variable 'instructions' (60% confidence)
src/jitsu/models/core.py:80: unused variable 'context_targets' (60% confidence)
src/jitsu/models/core.py:81: unused variable 'anti_patterns' (60% confidence)
src/jitsu/models/core.py:82: unused variable 'verification_commands' (60% confidence)
src/jitsu/models/core.py:86: unused variable 'completion_criteria' (60% confidence)
src/jitsu/models/core.py:87: unused variable 'context_injection' (60% confidence)
src/jitsu/models/core.py:94: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:96: unused variable 'phase_id' (60% confidence)
src/jitsu/models/core.py:97: unused variable 'status' (60% confidence)
src/jitsu/models/core.py:98: unused variable 'artifacts_generated' (60% confidence)
src/jitsu/models/core.py:99: unused variable 'agent_notes' (60% confidence)
src/jitsu/models/core.py:100: unused variable 'verification_output' (60% confidence)
src/jitsu/models/core.py:103: unused class 'ResumeResult' (60% confidence)
src/jitsu/models/core.py:106: unused variable 'model_config' (60% confidence)
src/jitsu/models/core.py:108: unused variable 'phase_id' (60% confidence)
src/jitsu/models/core.py:109: unused variable 'status' (60% confidence)
src/jitsu/models/core.py:110: unused variable 'reason' (60% confidence)
src/jitsu/models/execution.py:11: unused variable 'model_config' (60% confidence)
src/jitsu/models/execution.py:13: unused variable 'filepath' (60% confidence)
src/jitsu/models/execution.py:14: unused variable 'content' (60% confidence)
src/jitsu/models/execution.py:20: unused variable 'model_config' (60% confidence)
src/jitsu/models/execution.py:22: unused variable 'tool_name' (60% confidence)
src/jitsu/models/execution.py:23: unused variable 'arguments' (60% confidence)
src/jitsu/models/execution.py:29: unused variable 'model_config' (60% confidence)
src/jitsu/models/execution.py:31: unused variable 'thoughts' (60% confidence)
src/jitsu/models/execution.py:32: unused variable 'action' (60% confidence)
src/jitsu/models/execution.py:38: unused variable 'model_config' (60% confidence)
src/jitsu/models/execution.py:40: unused variable 'summary' (60% confidence)
src/jitsu/models/execution.py:41: unused variable 'trimmed' (60% confidence)
src/jitsu/models/execution.py:42: unused variable 'failed_cmd' (60% confidence)
src/jitsu/models/execution.py:43: unused variable 'failing_file' (60% confidence)
```

## 2. Cognitive Complexity (Complexipy)

```text
────────────────────────────────────────────────────────────────── 🐙 complexipy ───────────────────────────────────────────────────────────────────
                                         No files were found with functions. No complexity was calculated.                                          
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
