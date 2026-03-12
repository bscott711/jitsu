"""Vulture whitelist file."""

# Typer CLI Commands
main_callback
init
submit
queue_ls
queue_clear
auto

# Pydantic V2 Configs & LLM Fields
model_config
thoughts

# Pytest Fixtures
clear_state

# Prompts
EXECUTOR_RECOVERY_PROMPT
VERIFICATION_SUMMARY_RULE
TAG_INSTRUCTIONS
TAG_CONTEXT_MANIFEST
TAG_CONTEXT_DETAIL
TAG_PRIORITY_RECAP
TAG_TASK_SPEC
