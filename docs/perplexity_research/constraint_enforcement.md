# Jitsu v2: Constraint Stack Recommendation

## Current State Assessment

The v2 refactor is architecturally excellent. The DDD/DIP cleanup is complete: `JitsuOrchestrator`, `EpicStorage`, `LLMClientFactory`, `CommandRunner`, `ToolHandlers`, `ToolRegistry`, and centralized `prompts.py` are all landed. The codebase is clean: 100% test coverage, 0 Pyright errors, 0 Ruff violations, all complexity within bounds per the v2 audit.[1]

The most important insight from reading the full source is that **Jitsu already has the right skeleton for every constraint pattern discussed in this conversation** — it just needs them hardened in three precise places:

1. `src/jitsu/models/execution.py` — the `FileEdit`/`ExecutionResult` contract
2. `src/jitsu/prompts.py` — `EXECUTOR_SYSTEM_PROMPT` and `PLANNER_MICRO_PROMPT`
3. `src/jitsu/core/compiler.py` — `ContextCompiler` output encoding

***

## Recommended Tech Stack

| Layer | Technology | Where in Jitsu |
| --- | --- | --- |
| **System prompt framing** | XML constraint tags | `EXECUTOR_SYSTEM_PROMPT` in `src/jitsu/prompts.py` |
| **Executor output contract** | JSON + `instructor` Mode.JSON + Pydantic | `ExecutionResult` / `FileEdit` in `models/execution.py` |
| **Token-level grammar enforcement** | `instructor` + schema masking via `LLMClientFactory` | `src/jitsu/core/client.py` |
| **Placeholder/incomplete code detection** | Post-`FileEdit` regex validator in `JitsuExecutor` | `src/jitsu/core/executor.py` |
| **JIT context encoding** | TOON for uniform arrays, Markdown for prose | `src/jitsu/core/compiler.py` `ContextCompiler` |
| **API/symbol allowlist** | Prefix-tree from `ASTProvider` output | New `validate_symbols()` step in `executor.py` |
| **Negative prompting** | `anti_patterns` field (already exists) + XML block in prompt | `AgentDirective.anti_patterns` → `ContextCompiler.build_preamble()` |

***

## 1. Hardening `EXECUTOR_SYSTEM_PROMPT`

The current `EXECUTOR_SYSTEM_PROMPT` instructs the agent to output valid `ExecutionResult` JSON and scopes it to `module_scope` and `anti_patterns`.  The upgrade is to wrap its constraint block in XML tags and add hard physical rules that survive Flash-class context drift:[1]

```python
# src/jitsu/prompts.py

EXECUTOR_SYSTEM_PROMPT = """\
You are an autonomous coding agent. Given a directive and relevant context, \
you must propose file edits to fulfill the task.

<output_contract>
Your output MUST be valid JSON matching the ExecutionResult schema.
No prose. No markdown fences around the JSON. No explanations outside the schema.
</output_contract>

<hard_constraints>
- NEVER rewrite an entire file. Each FileEdit MUST target only the changed region.
- NEVER emit placeholder text such as "# rest of code here", "...", \
"# TODO: implement", or "# existing code unchanged".
- NEVER reference a function, class, or module not present in <available_symbols>.
- NEVER add new third-party dependencies not present in <available_symbols>.
- Scope ALL edits strictly to the `module_scope` field of the directive.
</hard_constraints>

Scope: {module_scope}
Anti-Patterns: {anti_patterns}
"""
```

**Rationale:** XML tags on `<output_contract>` and `<hard_constraints>` are treated as high-salience semantic boundaries by Claude and Gemini Flash-family models due to training distribution.  The `anti_patterns` from `AgentDirective` are still injected dynamically — the XML block handles the *always-on* floor-level rules, `anti_patterns` handles phase-specific rules. This separation is clean and preserves the existing `build_preamble()` logic.[2] [1]

***

## 2. Hardening `ExecutionResult` / `FileEdit`

The current `FileEdit` model is:

```python
class FileEdit(BaseModel):
    filepath: str
    content: str
```

This is the **single most dangerous contract in the whole system** — it allows the model to write anything, including entire file rewrites and placeholder stubs.  Upgrade it with Pydantic field validators that act as a post-generation gate before `apply_edits()` ever runs:[1]

```python
# src/jitsu/models/execution.py
import re
from pydantic import BaseModel, field_validator, model_validator

PLACEHOLDER_PATTERNS = re.compile(
    r"(#\s*(rest of code|existing code|\.\.\.todo|insert here|unchanged|"
    r"implement this|your code here|add.*logic|placeholder))",
    re.IGNORECASE,
)

class FileEdit(BaseModel):
    model_config = ConfigDict(frozen=True)
    filepath: str
    content: str

    @field_validator("content")
    @classmethod
    def no_placeholders(cls, v: str) -> str:
        if PLACEHOLDER_PATTERNS.search(v):
            raise ValueError(
                "FileEdit content contains forbidden placeholder text. "
                "Regenerate with complete implementation."
            )
        return v

class ExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    thoughts: str
    edits: list[FileEdit]

    @model_validator(mode="after")
    def edits_not_empty(self) -> "ExecutionResult":
        if not self.edits:
            raise ValueError("ExecutionResult must contain at least one FileEdit.")
        return self
```

**Why this works:** `instructor` wraps LLM output and retries on `ValidationError` automatically (up to `max_retries`).  This means a placeholder response is **not just detected — it is automatically retried** with the validation error message appended to the prompt. The model sees its own mistake and must fix it. This is deterministic enforcement, not advisory prompting.[1]

***

## 3. Symbol Allowlist in `ContextCompiler` + `JitsuExecutor`

The `ASTProvider` already extracts structural skeletons with function/class signatures.  The next step is to build a symbol allowlist from that output and pass it into the executor context — then validate outgoing `FileEdit.content` against it.[1]

**In `ContextCompiler.compile_directive()`**, add a symbol manifest section:

```python
# src/jitsu/core/compiler.py (addition to compile_directive)

async def _build_symbol_manifest(self, targets: list[ContextTarget]) -> str:
    """Extract available symbol names from AST targets for allowlist injection."""
    symbols: list[str] = []
    for target in targets:
        if target.provider_name == "ast" or target.resolution_mode in (
            TargetResolutionMode.STRUCTURE_ONLY, TargetResolutionMode.AUTO
        ):
            ast_provider = self.providers.get("ast")
            if ast_provider:
                raw = await ast_provider.resolve(target.target_identifier)
                # Parse function/class names from AST skeleton output
                symbols += re.findall(r"^(?:def|class)\s+(\w+)", raw, re.MULTILINE)
    if not symbols:
        return ""
    # TOON-encoded for token efficiency on uniform arrays
    symbol_list = "\n".join(symbols)
    return f"<available_symbols>\n{symbol_list}\n</available_symbols>"
```

Then in `JitsuExecutor.execute_directive()`, validate the `FileEdit` content against this list before writing to disk:

```python
# src/jitsu/core/executor.py (addition to execute_directive)

def _validate_symbols(self, edits: list[FileEdit], allowed: set[str]) -> None:
    """Reject edits that call symbols not in the allowlist."""
    if not allowed:
        return  # no allowlist = permissive mode
    for edit in edits:
        # Check for called names not in allowed set (simple heuristic)
        called = set(re.findall(r"\b([a-z_][a-z0-9_]*)\s*\(", edit.content))
        unknown = called - allowed - PYTHON_BUILTINS
        if unknown:
            raise ValueError(
                f"FileEdit for {edit.filepath} calls unknown symbols: {unknown}. "
                f"Only these are available: {allowed}"
            )
```

**Rationale:** This directly mirrors MARIN's dependency-constrained decoding but implemented at the Python validation layer rather than token masking — which is the right place for Jitsu since you own the post-generation step.  The `instructor` retry loop will propagate the `ValueError` back to the model.[3]

***

## 4. TOON Encoding in `ContextCompiler`

For the JIT context injection — specifically for symbol tables, `context_targets` manifests, and provider lists — TOON's uniform-array format gives real token savings (≈40%) with better retrieval accuracy.  This fits naturally into `ContextCompiler`'s existing Markdown output as an optional encoding for array-type sections:[4]

```python
# src/jitsu/core/compiler.py

@staticmethod
def _to_toon(records: list[dict[str, str]], label: str) -> str:
    """Encode a uniform list of dicts as TOON for token-efficient injection."""
    if not records:
        return ""
    fields = list(records[0].keys())
    header = f"{label}[{len(records)}]{{" + ",".join(fields) + "}:"
    rows = "\n".join(",".join(str(r.get(f, "")) for f in fields) for r in records)
    return f"{header}\n{rows}"
```

**Use this in the Context Manifest section** of `compile_directive()` where you list resolved targets:

```markdown
<!-- Current output (Markdown) -->
- src/jitsu/core/executor.py → Full Source (file)
- src/jitsu/core/planner.py → Structural AST (ast)

<!-- TOON-encoded (saves ~40% tokens for this section) -->
context_manifest[2]{file,provider,mode}:
src/jitsu/core/executor.py,file,FULL_SOURCE
src/jitsu/core/planner.py,ast,STRUCTURE_ONLY
```

**Important:** Apply TOON only to the **manifest and symbol table sections**, not to the actual code/AST content blocks. The 2026 TOON benchmark confirms token savings are largest on uniform-array inputs.  Prose and code blocks should remain as Markdown.[5]

***

## 5. `LLMClientFactory` — Grammar Mode Configuration

The factory already centralizes `instructor` client creation.  Add a mode parameter so callers can request schema-enforced generation:[1]

```python
# src/jitsu/core/client.py

from enum import Enum
import instructor
from instructor import Mode

class LLMMode(Enum):
    JSON = Mode.JSON           # Current default — good for executor
    JSON_SCHEMA = Mode.JSON_SCHEMA  # Stricter — for planner epic generation
    TOOLS = Mode.TOOLS         # For MCP tool-style calls

class LLMClientFactory:
    @staticmethod
    def create(
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        mode: LLMMode = LLMMode.JSON,
    ) -> instructor.Instructor:
        from openai import OpenAI
        return instructor.from_openai(
            OpenAI(api_key=api_key, base_url=base_url),
            mode=mode.value,
        )
```

Use `LLMMode.JSON_SCHEMA` for the **planner** (generating `AgentDirective` arrays — structurally complex) and `LLMMode.JSON` for the **executor** (generating `ExecutionResult` — simpler flat structure).  The schema enforcement in `JSON_SCHEMA` mode provides token-level masking of invalid structures.[6] [7]

***

## 6. Wiring It Into the Autonomous Loop

Here is how all five layers compose in a single `auto` invocation on Jitsu itself, using real module paths:

``` bash
jitsu auto "Add TOON encoding to the context manifest section"

JitsuOrchestrator.execute_auto()
│
├─ run_plan()  ←─ LLMClientFactory(mode=JSON_SCHEMA)
│   └─ JitsuPlanner.generate_plan()
│       ├─ Pass 1: EpicBlueprint (macro phases)  ← PLANNER_MACRO_PROMPT
│       └─ Pass 2: AgentDirective[]              ← PLANNER_MICRO_PROMPT + VERIFICATION_RULE
│           anti_patterns: [
│             "Do not rewrite compiler.py entirely",
│             "Do not add imports outside the TOON helper method",
│             "Do not emit # rest of code here",
│           ]
│
├─ execute_phases(directive, compiler)
│   ├─ ContextCompiler.compile_directive()
│   │   ├─ build_preamble()        ← XML <hard_constraints> + anti_patterns
│   │   ├─ resolve_targets()       ← AST skeleton for compiler.py
│   │   ├─ _build_symbol_manifest()← ASTProvider → symbol allowlist
│   │   └─ _to_toon()              ← TOON-encoded context manifest
│   │
│   └─ JitsuExecutor.execute_directive(directive, compiled_context)
│       ├─ LLMClientFactory(mode=JSON)
│       ├─ instructor → ExecutionResult  ← schema-enforced JSON
│       │   └─ FileEdit.no_placeholders()  ← Pydantic validator gates output
│       ├─ _validate_symbols()     ← allowlist check before disk write
│       ├─ apply_edits()           ← only runs if all validators pass
│       └─ CommandRunner.run("just", "verify")  ← zero-regression gate
│
└─ finalize() → archive to epics/completed/
```

***

## What NOT to Change

Given the audit results and the current health of the codebase:[1]

- **Do not move to YAML** for any agent-facing contract. Your entire validation story is `instructor` + Pydantic + JSON. YAML has no constrained-decoding ecosystem support and its leniency could silently mismap to your frozen models.
- **Do not add TOON to executor output.** TOON is for input encoding only; the 2026 benchmark shows JSON still wins as a generation target.[5]
- **Do not change the `anti_patterns` field** to XML. It is already a clean Pydantic `list[str]` that flows through `build_preamble()` — that is exactly correct. The XML layer belongs only in the static prompt constants in `prompts.py`, not in the domain models.
- **The two planned epics** (`epic-27-architectural-consolidation`, `epic-28-executor-rollback`) are the right next priorities before adding constraint features — a rollback mechanism is essential before you tighten the execution loop, since tighter validation means more retries and potential partial-write states.[1]

Sources
[1] bscott711-jitsu
[2] 12 prompt engineering tips to boost Claude's output quality - Vellum <https://www.vellum.ai/blog/prompt-engineering-tips-for-claude>
[3] Towards Mitigating API Hallucination in Code Generated by LLMs ... <https://arxiv.org/abs/2505.05057>
[4] Token-Oriented Object Notation (TOON) – Compact, human ... - GitHub <https://github.com/toon-format/toon>
[5] Token-Oriented Object Notation vs JSON: A Benchmark of Plain and ... <https://arxiv.org/abs/2603.03306>
[6] How Structured Outputs and Constrained Decoding Work <https://letsdatascience.com/blog/structured-outputs-making-llms-return-reliable-json>
[7] Constrained Decoding: Grammar-Guided Generation for Structured ... <https://mbrenndoerfer.com/writing/constrained-decoding-structured-llm-output>
