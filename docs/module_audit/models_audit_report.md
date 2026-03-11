# Models Module Architectural Audit Report

## 1. Open/Closed Principle & DRY Violations (Provider Literal)

**Nature of Violation:** In `src/jitsu/models/core.py`, the `ContextTarget` model has a hardcoded `Literal` for `provider_name`:

```python
provider_name: Literal["file", "ast", "tree", "pydantic", "env_var", "git", "markdown_ast"]
```

- **Impact:** This violates the Open/Closed Principle. If a new context provider is added to the system (e.g., a "database" provider or "web_search" provider), the foundational Pydantic models must be modified to accept the new literal string. This also duplicates the knowledge of available providers, which is already hardcoded in `ContextCompiler.__init__`.
- **Fix:** Instead of a hardcoded `Literal`, the model should ideally validate against a dynamic registry of available providers, or accept a standard `str` but enforce loose validation during the instantiation phase. If a strong type is required, it should be an `Enum` generated dynamically or maintained in a central configuration module, rather than repeated literal strings.

## 2. Hardcoded Instruction Strings in Pydantic Fields

**Nature of Violation:** `AgentDirective.verification_commands` contains a hardcoded description string:
`description="Commands to verify the phase is complete. You MUST strictly follow the verification constraints defined in the PROJECT RULES (e.g., this MUST include 'just verify')."`

- **Impact:** Model schema documentation strings should describe the data type, not encode prompt engineering instructions meant for the LLM. Placing prompt engineering instructions in the schema description fields tightly couples the data model to the LLM agent's behavior.
- **Fix:** Prompt engineering rules (like "MUST include 'just verify'") should be injected via the `JitsuPlanner`'s system prompts, not hardcoded into the data models. The description should just be `"Commands to verify the phase is complete."`

## 3. General Architecture Observations

- The models are mostly well-structured immutable data vehicles (`ConfigDict(frozen=True)`).
- There are no `# noqa` or `# pragma` markers to clean up within the models.
- Tests in `tests/models/test_core.py` enforce immutability and default values effectively.
