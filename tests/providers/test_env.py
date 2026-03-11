"""Unit tests for the EnvVarProvider."""

import os
from unittest.mock import patch

import pytest

from jitsu.core.compiler import ContextCompiler
from jitsu.models.core import AgentDirective, ContextTarget, TargetResolutionMode
from jitsu.providers.env import EnvVarProvider


@pytest.mark.asyncio
async def test_env_var_provider_resolve_existing() -> None:
    """Test resolving an existing environment variable."""
    provider = EnvVarProvider()
    with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
        result = await provider.resolve("TEST_VAR")
        assert result == "test_value"


@pytest.mark.asyncio
async def test_env_var_provider_resolve_missing() -> None:
    """Test resolving a missing environment variable."""
    provider = EnvVarProvider()
    with patch.dict(os.environ, {}, clear=True):
        result = await provider.resolve("MISSING_VAR")
        assert result == "Not Set"


def test_env_var_provider_name() -> None:
    """Test the provider name."""
    provider = EnvVarProvider()
    assert provider.name == "env_var"


@pytest.mark.asyncio
async def test_env_var_integration_with_compiler() -> None:
    """Test that ContextCompiler can use EnvVarProvider."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="test-epic",
        phase_id="test-phase",
        module_scope="test-scope",
        instructions="test-instructions",
        context_targets=[
            ContextTarget(
                target_identifier="ENV_INTEGRATION_TEST",
                provider_name="env_var",
                resolution_mode=TargetResolutionMode.AUTO,
                is_required=True,
            )
        ],
    )

    with patch.dict(os.environ, {"ENV_INTEGRATION_TEST": "compiler_works"}):
        compiled = await compiler.compile_directive(directive)
        assert "compiler_works" in compiled
        assert "Environment Variable" in compiled
