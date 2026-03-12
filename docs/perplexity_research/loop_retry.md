# The Critical Bug to Understand First

Before recommending a mechanism, there's a structural flaw in the current `execute_directive` loop that matters for this entire discussion. On a retry, the code does:[1]

```python
user_message = base_user_message
if last_error:
    user_message = f"VERIFICATION FAILURE\n{last_error}\nPlease fix the errors above."
```

The `=` on the second line **replaces** `base_user_message` entirely. On retry, the flash model receives *only* the error — the original directive instructions, completion criteria, and the entire compiled JIT context are gone. The agent is flying blind. This is almost certainly responsible for multi-retry failures spiraling into nonsense, because the model has lost its `module_scope`, `anti_patterns`, and target file context. The fix is the foundation of everything below.

***

## The Most Natural Fit: The Architecture Already Has All the Parts

Jitsu's layered design is explicitly built to solve exactly this problem. Every component you need already exists — the issue is wiring them together correctly inside the recovery loop.

### The 4 Natural Hooks

| Problem | Jitsu mechanism already available | What's missing |
| --- | --- | --- |
| Flash model loses context on retry | `ContextCompiler.resolve_auto()` + `base_user_message` must persist | Recovery prompt is replacing context rather than augmenting it |
| Full noisy stderr sent on failure | `run_verification` joins all stderr | A first-block extractor before the join |
| No monotonicity / spiral check | `max_retries = 3` exists | A failure-count comparison between attempts |
| No designed escape signal | `PhaseStatus.STUCK` enum already in `jitsu.models.core` | `execute_directive` never emits it — it just returns `False` silently |

[1]

***

## The Structural Patterns, Mapped to Jitsu's Layers

### 1. New constant in `src/jitsu/prompts.py` (Layer 0)

Add `EXECUTOR_RECOVERY_PROMPT` alongside `EXECUTOR_SYSTEM_PROMPT`. The key rule: the recovery prompt **augments** the base user message, it never replaces it.[1]

```python
EXECUTOR_RECOVERY_PROMPT = """\
--- PREVIOUS VERIFICATION FAILURE (Attempt {attempt} of {max_retries}) ---
Command: {command}
Outcome: {summary_line}

First failure block:


{trimmed_error}

---

AST skeleton of affected file ({failed_file}):
{ast_skeleton}
---

Your previous edit did not pass verification. Re-read your original directive and the context above.
Make the MINIMAL change required to fix the error shown. Do NOT modify files outside of: {module_scope}.
If you cannot determine a safe fix, output an empty `edits` list and explain in `thoughts`.
"""
```

This lives in `src/jitsu/prompts.py` with zero dependency violations — it's a pure string constant.[1]

### 2. First-failure extractor in `run_verification` (Layer 1 — `executor.py`)

`run_verification` currently joins ALL stderr from ALL commands. Instead, extract only the first actionable block, which aligns directly with Jitsu's AST-first, noise-stripping philosophy.[1]

```python
import re

def _extract_first_failure_block(stderr: str, max_lines: int = 15) -> tuple[str, str]:
    """Return (summary_line, trimmed_block) from raw stderr."""
    lines = stderr.strip().splitlines()
    # Find first 'FAILED' or 'error:' line as the anchor
    anchor = next(
        (i for i, l in enumerate(lines) if "FAILED" in l or "error:" in l.lower()),
        0,
    )
    block_start = max(0, anchor - 2)
    trimmed = "\n".join(lines[block_start : block_start + max_lines])
    summary = lines[anchor] if lines else "unknown error"
    return summary, trimmed

def run_verification(self, commands: list[str]) -> tuple[bool, str, str, str]:
    """Returns (passed, summary, first_trimmed_block, failed_command)."""
    for cmd in commands:
        res = self.runner.run(cmd)
        if res.returncode != 0:
            summary, block = _extract_first_failure_block(res.stderr)
            return False, summary, block, cmd
    return True, "", "", ""
```

The return signature change flows cleanly into `execute_directive` — the orchestrator now has enough structured data to fill `EXECUTOR_RECOVERY_PROMPT`.[1]

### 3. Re-compile targeted context on retry (Layer 1 → Layer 2)

After a failure, Jitsu knows the exact failing file from the traceback. Rather than re-sending the full initial `compiler_output`, use `ContextCompiler.resolve_auto()` to pull only the AST skeleton of the failing file.[1]

```python
# Inside execute_directive, on retry:
failed_file = _extract_file_from_error(trimmed_error)  # simple regex on traceback
ast_skeleton = ""
if failed_file and compiler:
    ast_skeleton, _ = await compiler.resolve_auto(failed_file, "ast")

recovery_suffix = EXECUTOR_RECOVERY_PROMPT.format(
    attempt=attempts + 1,
    max_retries=max_retries,
    command=failed_cmd,
    summary_line=summary,
    trimmed_error=trimmed_error,
    failed_file=failed_file or "unknown",
    ast_skeleton=ast_skeleton or "(not available)",
    module_scope=directive.module_scope,
)
# CRITICAL: augment, do not replace
user_message = base_user_message + "\n\n" + recovery_suffix
```

This is architecturally native — `ContextCompiler.resolve_auto` is *designed* for Progressive Disclosure exactly like this, and the fallback chain (AST → Pydantic → FileState) means it will always return something useful.[1]

### 4. Monotonicity guard (Layer 1 — orchestrator / executor)

Track the number of *remaining* failures across attempts and stop if the model isn't improving:[1]

```python
prev_fail_count = float("inf")

while attempts < max_retries:
    # ... run LLM, apply edits ...
    success, summary, trimmed_error, failed_cmd = self.run_verification(...)
    if success:
        return True

    # Monotonicity: count failures in output (ruff/pytest emit counts)
    current_fail_count = _count_failures(summary)  # parse "2 failed" or "E " lines
    if current_fail_count >= prev_fail_count and attempts > 0:
        logger.warning("Non-improving retry detected. Stopping early.")
        break  # don't waste another token budget attempt

    prev_fail_count = current_fail_count
    attempts += 1
```

### 5. `PhaseStatus.STUCK` as the designed spiral escape hatch (Layer 0 → Layer 1)

`PhaseStatus.STUCK` already exists in `jitsu.models.core` — it's the model's designed escape valve. Currently, `execute_directive` just returns `False` silently. For the MCP path to also benefit from the spiral guard, the state manager needs to know the phase stalled, not just failed.[1]

```python
# In execute_directive, after exhausting retries:
if self.state_manager:  # injected optionally for auto path
    self.state_manager.record_report(PhaseReport(
        phase_id=directive.phase_id,
        status=PhaseStatus.STUCK,
        agent_notes=f"Exhausted {max_retries} retries. Last error: {trimmed_error[:200]}",
        verification_output=last_raw_stderr,
    ))
return False
```

For the **MCP path** (Antigravity/Cursor), the agent can emit `STUCK` autonomously via `jitsu_report_status`, which is already in the tool spec. The `JitsuStateManager` observing `STUCK` is the natural point to halt the queue rather than pulling the next phase.[1]

***

## The Resulting `execute_directive` Skeleton

Putting it all together, the corrected method structure looks like:

```python
def execute_directive(
    self,
    directive: AgentDirective,
    compiler_output: str,
    compiler: ContextCompiler | None = None,
) -> bool:
    max_retries = 3
    attempts = 0
    last_error_context: dict = {}
    prev_fail_count = float("inf")

    system_prompt = EXECUTOR_SYSTEM_PROMPT.format(
        module_scope=directive.module_scope,
        anti_patterns="\n".join(directive.anti_patterns),
    )
    base_user_message = (
        f"Directive: {directive.instructions}\n"
        f"Completion Criteria: {', '.join(directive.completion_criteria)}\n"
        f"Context:\n{compiler_output}"
    )

    while attempts < max_retries:
        user_message = base_user_message
        if last_error_context:                        # augment, never replace
            user_message += "\n\n" + EXECUTOR_RECOVERY_PROMPT.format(**last_error_context)

        try:
            result = self.client.chat.completions.create(...)
            # Scope guard: reject edits outside module_scope on retries
            safe_edits = [
                e for e in result.edits
                if attempts == 0 or directive.module_scope in e.filepath
            ]
            self.apply_edits(safe_edits)

            success, summary, trimmed, failed_cmd = self.run_verification(...)
            if success:
                return True

            current_fail_count = _count_failures(summary)
            if current_fail_count >= prev_fail_count and attempts > 0:
                break  # monotonicity: stop early

            prev_fail_count = current_fail_count
            ast_skeleton = ""
            if compiler:
                failed_file = _extract_file_from_error(trimmed)
                if failed_file:
                    ast_skeleton, _ = asyncio.run(compiler.resolve_auto(failed_file, "ast"))

            last_error_context = dict(
                attempt=attempts + 1, max_retries=max_retries,
                command=failed_cmd, summary_line=summary,
                trimmed_error=trimmed, failed_file=failed_file or "unknown",
                ast_skeleton=ast_skeleton or "(unavailable)",
                module_scope=directive.module_scope,
            )
            attempts += 1

        except openai.APIStatusError as e:
            typer.secho(f"Execution API Error: {e.status_code} {e.message}", ...)
            return False  # fast-fail, don't retry
        except InstructorRetryException:
            typer.secho("Executor Error: Failed to generate valid schema.", ...)
            return False  # fast-fail

    # Emit STUCK so state_manager / MCP path knows the loop exhausted
    self._emit_stuck(directive, last_error_context)
    return False
```

***

## What NOT to Do in This Framework

- **Don't send AST diffs to the flash model** — Jitsu's `GitProvider` can produce them, but they're for the orchestrator's risk scoring, not for model consumption. Use the `GitProvider` in `execute_phases` to check diff size *before* allowing another retry.
- **Don't re-send `compiler_output` in full on every retry** — the initial compile is expensive and already in the model's context via `base_user_message`. Only augment with the targeted AST skeleton of the failing file.
- **Don't use `jitsu_request_context` from within `execute_directive`** — that tool is for the MCP agent path (Antigravity/Cursor). In the `auto` path, call `ContextCompiler.resolve_auto()` directly. Mixing the transport layer into the executor would violate the Layer 3 → Layer 1 dependency rule.[1]

***

## Summary: The Epic You'd Write

If you were writing this as a Jitsu epic (`jitsu plan "Harden the executor self-correction loop"`), the natural phases would be:

1. **`phase-01-recovery-prompt`** — Add `EXECUTOR_RECOVERY_PROMPT` + `VERIFICATION_SUMMARY_RULE` to `src/jitsu/prompts.py`
2. **`phase-02-first-failure-extractor`** — Refactor `run_verification` in `executor.py` to return `(bool, summary, trimmed_block, failed_cmd)` using `_extract_first_failure_block`
3. **`phase-03-augment-not-replace`** — Fix `execute_directive` to append the recovery prompt to `base_user_message` and inject the AST skeleton of the failing file via `ContextCompiler.resolve_auto`
4. **`phase-04-monotonicity-scope-guard`** — Add the `prev_fail_count` guard and `module_scope` filter on `FileEdit` paths for retry ≥ 1
5. **`phase-05-stuck-signal`** — Wire `PhaseStatus.STUCK` into `execute_directive`'s exhaustion path and add a `JitsuStateManager.on_stuck` hook to halt the queue

All five phases would pass `just verify` independently, and the net result is a self-correcting loop that is provably bounded, context-preserving, and architecturally coherent with Jitsu's existing layer contracts.

Sources
[1] bscott711-jitsu
