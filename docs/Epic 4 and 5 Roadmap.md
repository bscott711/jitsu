# Epic 4 and 5 Roadmap

The horizon should be centered on one thing: make Jitsu compile a **smaller, stricter, more execution-ready payload before the agent ever starts coding.** Epic 3 gave you the IPC plumbing needed to submit work into a live server, but your docs and compiler still leave too much preparation to the agent, and the current compiler only recently registers the AST provider rather than making AST-first context assembly a core optimization path.[1]

## Next epic

I would make the next epic **“Compiler-first context optimization”** because the repo’s stated mission is to compile ground-truth context from code, and the docs explicitly position AST extraction as the token-saving structural view that should replace raw source when possible.[1]

The immediate gap is that `ContextCompiler` currently just loops through requested `context_targets` and appends provider output, while the architecture docs say the compiler should be the JIT engine that builds a highly optimized payload from AST, schemas, and file state.  The AST provider is present, registered under `"ast"`, and designed to return structural skeletons instead of full source, but the workflow still depends on directives manually asking for that provider rather than having Python automatically prefer AST where appropriate.[1]

### Epic 4 goals

| Phase | What to build | Why it matters |
| --- | --- | --- |
| 4.1 | Add a **context planning layer** inside `ContextCompiler` that decides when to use `ast`, `file_state`, or `pydantic_v2` automatically [1] | This moves preparation from the agent into Python, which matches your stated goal of saving tokens before handoff [1] |
| 4.2 | Add a `ContextTarget` mode or compiler policy such as `AUTO`, `STRUCTURE_ONLY`, `FULL_SOURCE`, `SCHEMA_ONLY` | This gives the directive engine a typed way to express token budgets and detail levels instead of forcing raw file dumps by default [1] |
| 4.3 | Emit a **compiled context manifest** in the Markdown payload, listing what was summarized, what was omitted, and how to request deeper context | Your docs already describe dynamic deep-context requests, so this makes the initial payload smaller while preserving an escape hatch [1] |
| 4.4 | Add tests for “AST preferred over file_state” and “fallback to file_state on AST failure” | Your repo enforces 100% coverage and strict test gates, so compiler policy needs to be covered as first-class behavior [1] |

## Epic after that

The epic after that should be **“Definition-of-done orchestration.”** Your docs promise a simple IDE loop of get phase, execute, report, but the repo’s actual delivery contract also includes `verify-fast`, strict typing, Ruff, and 100% coverage, which today still live mostly in `JustFile`, `pyproject.toml`, and lead-dev notes rather than in the directive model itself.[1]

### Epic 5 goals

- Extend `AgentDirective` with fields like `verification_commands`, `required_test_paths`, `completion_criteria`, and `context_budget`.[1]
- Have the compiler inject repo-wide invariants automatically, such as “no stdout logging,” “run `verify-fast` before success,” and “do not report done if coverage drops below 100%.”[1]
- Make `jitsu_report_status` reject `SUCCESS` unless required verification artifacts are present, or at least mark the phase `STUCK`/`FAILED` with structured feedback when quality gates were skipped.[1]

That epic matters because your own experience on Epic 3 showed the current system can build the feature but still miss tests and coverage obligations until you manually restate them.[1]

## AST-first handoff

If token efficiency is the priority, the default handoff should become **AST + schema + only the smallest necessary source slices.** That fits the original AST design doc, which says the provider exists to extract classes, methods, functions, signatures, and docstrings without sending full bodies, specifically to save context window space.[1]

A practical compiler policy would look like this:

- For `.py` files, send `ast` first.[1]
- For Pydantic models, send `pydantic_v2` schema instead of source.[1]
- Only send `file_state` for files the agent must edit directly, and even then prefer targeted snippets over whole-file dumps.[1]
- If a directive references many related files, precompute a **dependency summary** in Python and hand the agent a ranked shortlist rather than every file.[1]

That would better match the repo’s philosophy that the code is the source of truth and that Python should extract exact state programmatically instead of asking the LLM to discover it expensively from raw text.[1]

## Roadmap shape

Here is the roadmap I would use:

1. **Close Epic 3 formally** — treat IPC, submit, and server wiring as done in practice, even if completed-file movement remains manual.[1]
2. **Epic 4: Compiler-first optimization** — automatic AST/schema selection, context budgeting, fallback rules, and compact payload manifests.[1]
3. **Epic 5: Done-state enforcement** — typed verification requirements, automatic `verify-fast` expectations, and stricter success reporting.[1]
4. **Epic 6: Progressive disclosure** — implement `jitsu_request_deep_context` for on-demand expansion so the initial phase payload stays minimal.[1]

If you execute in that order, Jitsu shifts from “transport + providers” toward the thing your docs actually describe: a Python orchestrator that does the expensive reasoning and preparation work up front, then gives the agent only the minimum truthful context needed to act.[1]

If you want, I can turn this into a concrete Epic 4 JSON and Epic 5 JSON in your existing directive format.

Sources
[1] file-1.txt <https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/153862535/3298a89a-0848-4bd1-92cc-218817f79ca3/file-1.txt>
