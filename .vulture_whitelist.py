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
# GitProvider (Sandbox Workflow)
get_current_branch
create_and_checkout_branch
checkout_branch
merge_branch
delete_branch
label

# Pydantic Validators
validate_phases_not_empty
validate_provider_name
validate_module_scope_not_empty
enforce_zero_bypass_verification
