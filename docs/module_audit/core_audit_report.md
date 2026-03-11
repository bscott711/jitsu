# Core Module Architectural Audit Report

## 1. Tight Coupling and Dependency Injection Violations

**Nature of Violation:** `JitsuPlanner` and `JitsuExecutor` directly instantiate their LLM clients (`openai.OpenAI`, `instructor.from_openai`), access the environment (`os.environ.get`), and handle `.env` loading (`dotenv.load_dotenv()`) within their methods.

- This violates the Dependency Inversion Principle. They should receive an initialized `LLMClient` (or a protocol) via constructor injection.
- **Impact:** Testing requires massive sets of `@patch` decorators for `os`, `dotenv`, `openai`, and `instructor`, making tests brittle and tied to implementation details.

## 2. Hardcoded Prompts

**Nature of Violation:** System prompts are embedded directly as strings within `JitsuPlanner.generate_plan` and `JitsuExecutor.execute_directive`.

- This violates the Separation of Concerns. Prompts should be externalized into domain-specific template files (e.g. `.md` or `.j2` using Jinja) and loaded via an injected prompt provider.

## 3. Violations of the Open/Closed Principle

**Nature of Violation:** `ContextCompiler` hardcodes the instantiation and registration of providers (`FileStateProvider`, `PydanticProvider`, etc.) inside its `__init__` method.

- If a user or future developer wants to add a new context provider, they must modify `compiler.py`.
- **Fix:** Implement a Provider Registry where providers can be dynamically registered (e.g., via entry points or an explicit `register_provider` method).

## 4. Platform and System Coupling (`subprocess.run`)

**Nature of Violation:** `JitsuExecutor` calls `subprocess.run()` directly to run verification commands for directives.

- This tightly couples the executor to the host OS and makes testing difficult (requiring `patch("subprocess.run")`).
- **Fix:** Extract command execution into a discrete `CommandRunner` or sandbox interface, which could be mocked cleanly during testing or extended for containerized execution.

## 5. DRY (Don't Repeat Yourself) Violations

**Nature of Violation:** Client initialization logic (`dotenv.load_dotenv()`, checking for `OPENROUTER_API_KEY`, setting up `instructor.from_openai()`) is perfectly duplicated across `executor.py` and `planner.py`.

## Recommended Structural Fixes

1. **Extract LLM Factory**: Create an `LLMConfig` or `LLMClientFactory` responsible for environment loading and client initialization. Inject this into Planner and Executor.
2. **Prompt Templating Module**: Extract hardcoded prompt logic into a centralized `prompts` directory loaded dynamically.
3. **Provider Registry**: Refactor `ContextCompiler` to accept a registry of providers rather than hardcoding them.
4. **Extract Command Runner**: Isolate the verification command execution from `JitsuExecutor` into a `CommandRunner` protocol.
