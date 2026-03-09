"""Tests for the Context Compiler engine."""

from unittest.mock import AsyncMock

import pytest

from jitsu.core.compiler import ContextCompiler
from jitsu.models.core import AgentDirective, ContextTarget


@pytest.mark.asyncio
async def test_compile_empty_targets() -> None:
    """Test compiling a directive with no context targets."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="do stuff",
    )
    res = await compiler.compile_directive(directive)
    assert "No specific context targets requested" in res
    assert "do stuff" in res


@pytest.mark.asyncio
async def test_compile_with_anti_patterns() -> None:
    """Test compiling a directive that includes anti-patterns."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="do stuff",
        anti_patterns=["Do not use MD5"],
    )
    res = await compiler.compile_directive(directive)
    assert "## Anti-Patterns" in res
    assert "- Do not use MD5" in res


@pytest.mark.asyncio
async def test_compile_unknown_provider_required() -> None:
    """Test compiling with a required target requesting an unknown provider."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="fake_provider",
                target_identifier="test_target",
                is_required=True,
            )
        ],
    )
    res = await compiler.compile_directive(directive)
    assert "### [FAILED] test_target" in res
    assert "Unknown provider 'fake_provider'" in res


@pytest.mark.asyncio
async def test_compile_unknown_provider_optional() -> None:
    """Test compiling with an optional target requesting an unknown provider."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="fake_provider",
                target_identifier="test_target",
                is_required=False,
            )
        ],
    )
    res = await compiler.compile_directive(directive)
    assert "[FAILED]" not in res


@pytest.mark.asyncio
async def test_compile_valid_provider() -> None:
    """Test compiling with a successfully resolved target."""
    compiler = ContextCompiler()

    # We use AsyncMock because the compiler expects resolve() to be awaitable
    mock_provider = AsyncMock()
    mock_provider.resolve.return_value = "MOCK_FILE_CONTENT"
    compiler._providers["mock_provider"] = mock_provider  # noqa: SLF001

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="mock_provider",
                target_identifier="test_target",
            )
        ],
    )
    res = await compiler.compile_directive(directive)
    assert "MOCK_FILE_CONTENT" in res
    mock_provider.resolve.assert_called_once_with("test_target")
