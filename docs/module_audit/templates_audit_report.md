# Templates Module Architectural Audit Report

## 1. Minimal Logic and Code Coverage

**Nature of Violation:** The `src/jitsu/templates` module contains solely static files (`rules.md`, `justfile.tmpl`, and an empty `__init__.py`). There are no python logic files, and consequently, there is no `tests/templates/` directory.

- **Impact:** While storing static internal files here is perfectly acceptable and arguably a good Separation of Concerns, the mechanism for interacting with these templates is tightly coupled in `src/jitsu/cli/main.py` inside the `init()` command.
- **Fix:** Ensure that as the templates grow more complex, any templating logic (like Jinja parsing if introduced) is housed in a `TemplateManager` class inside the templates module rather than keeping it all inside the CLI `init` command.

## 2. Lack of Centralized Template Loading

**Nature of Violation:** `cli/main.py` directly uses `importlib.resources.files("jitsu.templates").joinpath("rules.md").read_text()`.

- **Impact:** If other modules eventually need access to these rules (e.g., the planner for dynamic prompt building), they will also need to replicate `importlib.resources` boilerplate.
- **Fix:** Add a `TemplateLoader` utility to `src/jitsu/templates/__init__.py` or a dedicated `loader.py` that abstracts away the parsing and importing logic of these internal package resources.

## Conclusion

The templates module currently adheres to standard packaging patterns. The primary architectural improvements involve decoupling the loading mechanism from the CLI logic.
