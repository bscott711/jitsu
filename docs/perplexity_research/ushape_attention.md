# U-Shape Attention

Jitsu is already very close to a “SOTA” execution setup; what you mainly need is a disciplined, repeatable structure at the **execution** level that (a) keeps global rules in system, (b) keeps the task and Definition of Done late, and (c) positions file/AST context either very early (summary) or immediately before the question, never in the undifferentiated middle.[1]

## 1. System vs user: where rules go

For execution agents (“Agent Frank” / Flash‑class):

- Put **project‑wide and protocol rules** in the system message:
  - DDD layer rules (`jitsu.models` never importing providers/server, etc.).[1]
  - `.jitsurules` / Jitsu Workflow Protocol constraints (must call `jitsu_get_next_phase`, `jitsu_request_context`, `just verify`, MCP stdout safety).[1]
  - Global engineering standards (100% coverage, Pyright strict, no boilerplate slop).[1]
- Put **phase‑specific task + DoD** in the user message:
  - The `AgentDirective.instructions`, `anti_patterns`, `completion_criteria`, and `verification_commands` that ContextCompiler already emits as a “Phase Directive”.[1]

This aligns with how you already separate the orchestrator prompt (architect/planner) from the execution agent JSON schema, and it matches training assumptions of frontier models.[1]

## 2. Where to place AST / file context

Given the U‑shaped “lost in the middle” behavior, you want:

- Early, small summaries:
  - A short “Context Manifest” summary of each target (what it is, how it was resolved) near the top of the compiled user message.[1]
- Late, detailed code:
  - The **actual AST/file slices** that matter for the current directive placed in a clearly labeled block *immediately before* the “TASK / OUTPUT” instructions.[1]
- Avoid:
  - Long, homogeneous blocks of AST or full files between two sets of instructions; that’s exactly where models under‑use content.[1]

Your `ContextCompiler.build_preamble_directive` + `resolve_targets` already gives you a good separation; the change is the ordering and labeling of those sections in the final Markdown.[1]

## 3. Concrete execution‑prompt skeleton (Jitsu‑style)

Here’s a concrete structure for the **execution** prompt body that Jitsu’s `ContextCompiler.compiledirective` can move toward (this is inside the user message; system carries the long‑lived rules):

```text
<TITLE>
Jitsu Phase Directive: {phase_id}
Epic: {epic_id}
Module Scope: {module_scope}
</TITLE>

<RULES_SUMMARY>
You are operating under Jitsu orchestration. Key protocol rules:
- Always trust the JIT context from this prompt, not prior memory.
- Use jitsu_request_context if information is missing.
- Run `just verify` for verification, never ad‑hoc commands.
- Respect anti-patterns and module_scope strictly.
</RULES_SUMMARY>

<INSTRUCTIONS>
{directive.instructions}
</INSTRUCTIONS>

<ANTI_PATTERNS>
{one-bullet-per-anti-pattern}
</ANTI_PATTERNS>

<DEFINITION_OF_DONE>
{one-bullet-per-completion-criterion}
</DEFINITION_OF_DONE>

<VERIFICATION_COMMANDS>
{one-bullet-per-verification-command}
</VERIFICATION_COMMANDS>

<JIT_CONTEXT_MANIFEST>
{one-line summary per ContextTarget: path, provider, mode, required?}
Example:
- target: src/jitsu/core/executor.py | provider: ast | mode: AUTO | manifest: Summarized Structural AST
</JIT_CONTEXT_MANIFEST>

<JIT_CONTEXT_DETAIL>
# For each resolved context target actually needed

## File: src/jitsu/core/executor.py (mode: AST)
```python
# pruned AST / signature skeleton here
```

## File: src/jitsu/core/executor.py (mode: FULL_SOURCE, focused slice)

```python
# narrowed full-source excerpt for the function(s) to edit
```

## File: src/jitsu/core/planner.py (mode: STRUCTURE_ONLY)

```python
# signatures and docstrings
```

</JIT_CONTEXT_DETAIL>

<PRIORITY_RECAP>
In this phase you MUST:

1) Work only within {module_scope} and EDITABLE files indicated above.
2) Respect all Anti-Patterns.
3) Satisfy every Definition of Done item.
4) Use the provided JIT_CONTEXT_DETAIL; request more via jitsu_request_context if missing.
</PRIORITY_RECAP>

<TASK_AND_OUTPUT_SPEC>
Task: Apply the necessary edits to fulfill the Definition of Done.

Output:

1) Brief explanation of the change and why it preserves invariants.
2) A JSON object matching the ExecutionResult schema (from jitsu.models.execution).
</TASK_AND_OUTPUT_SPEC>

Notes:

- Global protocol rules live in system; `<RULES_SUMMARY>` is a compressed echo in the user message, close to the actual task.[1]
- The **JIT_CONTEXT_DETAIL** block sits just before the **PRIORITY_RECAP** and **TASK_AND_OUTPUT_SPEC**, which keeps both the evidence and the question in the high‑attention tail of the context.[1]
- The **Manifest** section provides an early, compact view so even small models have a top‑of‑prompt “map” of what’s coming.[1]

## 4. Avoiding “lost in the middle” in your compiler

Given your current `ContextCompiler` implementation:[1]

- Today it does:
  - Preamble (title, instructions, anti‑patterns, DoD, verification).
  - “JIT Context” section that inlines all resolved targets.
  - Optional “Compiled Context Manifest”.[1]
- To better exploit position bias, adjust to:
  1. Preamble (title + instructions/DoD/verification) – keep.
  2. Context Manifest (one‑line summary per target) – **move earlier**, right after instructions.
  3. Then *optionally*:
     - Non‑critical context (e.g., README snippets) in the mid‑section.
  4. Critical code/AST for the specific functions/files – **render last**, in a separate labeled block, immediately followed by a short recap and the explicit “Task / Output Spec”.[1]

That’s essentially a light refactor of `compiledirective` to:

- Split `targetparts` into “primary” vs “secondary” (you can use `TargetResolutionMode` + `is_required` as a heuristic).
- Emit secondary targets earlier, primary last, followed immediately by the task, instead of a flat concatenation.[1]

## 5. Example: prompt for `JitsuExecutor` edit

Suppose a directive from your completed epics asks to centralize all `openai` execution error handling in `JitsuExecutor` while preserving the existing CLI behavior.[1]

A strong execution prompt (user message) would look like:

```text
Jitsu Phase Directive: phase-executor-error-handling
Epic: epic-core-dependency-injection
Module Scope: src/jitsu/core/executor.py

<INSTRUCTIONS>
Centralize OpenAI-related error handling inside JitsuExecutor so that:
- openai.APIStatusError and InstructorRetryException are handled in one place.
- The existing typer.secho behavior and exit codes are preserved.
- No new global state is introduced.
</INSTRUCTIONS>

<ANTI_PATTERNS>
- Do NOT catch Exception broadly around the entire execute_directive flow.
- Do NOT print to stdout; use typer.secho with err=True only.
- Do NOT modify verification behavior or commands.
</ANTI_PATTERNS>

<DEFINITION_OF_DONE>
- All OpenAI-related errors are handled in a single helper or method.
- Existing CLI error messages remain semantically identical.
- Tests under tests/core/test_executor.py still pass with 100% coverage.
</DEFINITION_OF_DONE>

<VERIFICATION_COMMANDS>
- just verify
</VERIFICATION_COMMANDS>

<JIT_CONTEXT_MANIFEST>
- src/jitsu/core/executor.py | provider: file | mode: FULLSOURCE | REQUIRED
- tests/core/test_executor.py | provider: file | mode: FULLSOURCE | REQUIRED
</JIT_CONTEXT_MANIFEST>

<JIT_CONTEXT_DETAIL>
## File: src/jitsu/core/executor.py
```python
# full source, or a focused slice around execute_directive and its error handling
```

## File: tests/core/test_executor.py

```python
# full source or focused slice around tests that assert error behavior
```

</JIT_CONTEXT_DETAIL>

<PRIORITY_RECAP>

- Only edit src/jitsu/core/executor.py.
- Preserve existing user-facing error text.
- Keep tests and coverage behavior identical.
</PRIORITY_RECAP>

<TASK_AND_OUTPUT_SPEC>
Task: Propose the minimal refactor to centralize error handling under these constraints.

Output:

1) Short explanation of your changes.
2) ExecutionResult JSON describing file edits, including new/modified functions.
</TASK_AND_OUTPUT_SPEC>

This keeps the *directive text* and *file evidence* adjacent and prevents the large code block from being stranded between two instruction blocks.[1]

***

Sources
[1] bscott711-jitsu
