# Here is the master roadmap for Jitsu V3's Orchestration Pipeline

Milestone 1: The U-Curve Compiler (Attention Management)

Goal: Stop the model from "losing" instructions in the middle of massive file dumps.

Phase 1.1: XML Tag Standardization. Define strict string constants for INSTRUCTIONS, SECONDARY_CONTEXT, EDITABLE_CODE, PRIORITY_RECAP, and OUTPUT_SPEC.

Phase 1.2: The ContextCompiler Refactor. Rewire src/jitsu/core/compiler.py to enforce the U-Curve structure. The compiler must logically sort read-only context into the middle, and editable files at the very end.

Phase 1.3: Prompt Validation Suite. Update tests/core/test_compiler.py to aggressively assert the exact string ordering of these XML tags. If the prompt is out of order, the build fails.

Milestone 2: The Straitjacket (Diff-Only Protocol)

Goal: Revoke the model's physical ability to rewrite entire files.

Phase 2.1: Schema Redesign. Modify src/jitsu/models/execution.py. Deprecate the content string in FileEdit. Introduce a SearchReplaceBlock schema requiring search_text and replace_text.

Phase 2.2: Strict String Matching. Update src/jitsu/core/executor.py to perform literal string replacement. If search_text is not found exactly as written in the target file, raise a custom SearchBlockMismatchError. The file is left untouched.

Phase 2.3: Whitespace & Indentation Normalization. (The hardest part of diffs). Implement a utility in the Executor to handle trailing whitespace or indentation mismatches gracefully before failing the edit, ensuring minor formatting quirks don't trigger endless rejections.

Milestone 3: The API Gatekeeper (Hallucination Prevention)

Goal: Prevent the model from calling APIs or functions that do not exist.

Phase 3.1: AST Symbol Extraction. Enhance src/jitsu/providers/ast.py to extract a flat list of valid classes, functions, and imports from a given file.

Phase 3.2: Executor Pre-Flight Check. Before executor.py applies a replace_text block, it scans the new code for function calls. If it finds magic_function() and that symbol isn't in the AST allowlist, the edit is immediately rejected before saving to disk.

Milestone 4: The Recovery Loop (Self-Correction)

Goal: Prevent the hallucination spiral when tests or linters fail.

Phase 4.1: Failure Schema & Truncation. Create a VerificationFailure schema. Update src/jitsu/core/runner.py to capture pytest/ruff errors, strip ANSI escape codes, and extract only the last 15 lines of the first failure.

Phase 4.2: State Management & Monotonicity. Update src/jitsu/core/state.py to track retry_count. Implement the Monotonicity Guard: if Attempt 2 yields more failing tests than Attempt 1, abort the phase completely.

Phase 4.3: Recovery Prompt Injection. Update the ContextCompiler to detect a retry state. If true, inject the truncated VerificationFailure into the INSTRUCTIONS block, explicitly forbidding the model from repeating its last mistake.
