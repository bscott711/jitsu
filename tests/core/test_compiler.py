"""Tests for the Context Compiler engine."""

from unittest.mock import AsyncMock

import pytest

from jitsu.core.compiler import ContextCompiler
from jitsu.models.core import AgentDirective, ContextTarget, TargetResolutionMode


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


@pytest.mark.asyncio
async def test_compile_auto_ast_preference() -> None:
    """Test that AUTO mode prefers AST for .py files."""
    compiler = ContextCompiler()
    mock_ast = AsyncMock()
    mock_ast.resolve.return_value = "AST_OUTPUT"
    compiler._providers["ast"] = mock_ast  # noqa: SLF001

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="file_state",
                target_identifier="src/main.py",
                resolution_mode=TargetResolutionMode.AUTO,
            )
        ],
    )
    res = await compiler.compile_directive(directive)
    assert "AST_OUTPUT" in res
    assert "Summarized (Structural AST)" in res
    mock_ast.resolve.assert_called_once_with("src/main.py")


@pytest.mark.asyncio
async def test_compile_auto_fallback_to_file_on_ast_failure() -> None:
    """Test that AUTO mode falls back to file_state if AST fails."""
    compiler = ContextCompiler()
    mock_ast = AsyncMock()
    mock_ast.resolve.return_value = "### [FAILED] AST error"
    compiler._providers["ast"] = mock_ast  # noqa: SLF001

    mock_file = AsyncMock()
    mock_file.resolve.return_value = "FILE_CONTENT"
    compiler._providers["file_state"] = mock_file  # noqa: SLF001

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="none",
                target_identifier="src/main.py",
                resolution_mode=TargetResolutionMode.AUTO,
            )
        ],
    )
    res = await compiler.compile_directive(directive)
    assert "FILE_CONTENT" in res
    assert "Full Source" in res
    mock_ast.resolve.assert_called_once_with("src/main.py")
    mock_file.resolve.assert_called_once_with("src/main.py")


@pytest.mark.asyncio
async def test_compile_context_manifest_inclusion() -> None:
    """Test that the context manifest is included in the payload."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="file_state",
                target_identifier="README.md",
                resolution_mode=TargetResolutionMode.FULL_SOURCE,
            )
        ],
    )
    res = await compiler.compile_directive(directive)
    assert "## Compiled Context Manifest" in res
    assert "- `README.md`: **Full Source** (file_state)" in res


@pytest.mark.asyncio
async def test_compile_auto_pydantic_trigger() -> None:
    """Test that AUTO mode triggers Pydantic for symbols."""
    compiler = ContextCompiler()
    mock_pydantic = AsyncMock()
    mock_pydantic.resolve.return_value = "SCHEMA_OUTPUT"
    compiler._providers["pydantic_v2"] = mock_pydantic  # noqa: SLF001

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="none",
                target_identifier="jitsu.models.core.AgentDirective",
                resolution_mode=TargetResolutionMode.AUTO,
            )
        ],
    )
    res = await compiler.compile_directive(directive)
    assert "SCHEMA_OUTPUT" in res
    assert "Condensed (JSON Schema)" in res


@pytest.mark.asyncio
async def test_explicit_mode_failure_string_in_manifest() -> None:
    """Test explicit mode when the provider returns a failure string."""
    compiler = ContextCompiler()
    mock_file = AsyncMock()
    mock_file.resolve.return_value = "ERROR: something happened"
    compiler._providers["file_state"] = mock_file  # noqa: SLF001

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="any",
                target_identifier="t",
                resolution_mode=TargetResolutionMode.FULL_SOURCE,
            )
        ],
    )

    res = await compiler.compile_directive(directive)
    assert "Unknown provider 'any' or resolution failed for 't'." in res


@pytest.mark.asyncio
async def test_compile_explicit_schema_mode() -> None:
    """Test explicit SCHEMA_ONLY mode."""
    compiler = ContextCompiler()
    mock_pydantic = AsyncMock()
    mock_pydantic.resolve.return_value = "SCHEMA_JSON"
    compiler._providers["pydantic_v2"] = mock_pydantic  # noqa: SLF001

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="none",
                target_identifier="models.User",
                resolution_mode=TargetResolutionMode.SCHEMA_ONLY,
            )
        ],
    )
    res = await compiler.compile_directive(directive)
    assert "SCHEMA_JSON" in res
    assert "Condensed (JSON Schema)" in res


@pytest.mark.asyncio
async def test_explicit_mode_missing_provider_failure() -> None:
    """Test explicit mode failure when provider is missing."""
    compiler = ContextCompiler()
    del compiler._providers["ast"]  # noqa: SLF001

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="none",
                target_identifier="t",
                resolution_mode=TargetResolutionMode.STRUCTURE_ONLY,
            )
        ],
    )
    res = await compiler.compile_directive(directive)
    assert "FAILED" in res


@pytest.mark.asyncio
async def test_unknown_resolution_mode_internal() -> None:
    """Test internal _resolve_explicit with invalid mode."""
    compiler = ContextCompiler()
    # Use type: ignore to bypass enum check for testing
    res, provider = await compiler._resolve_explicit("target", "INVALID")  # type: ignore # noqa: SLF001
    assert res == ""
    assert provider == "none"
