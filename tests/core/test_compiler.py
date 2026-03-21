"""Tests for the Context Compiler engine."""

import asyncio
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest

from jitsu.core.compiler import ContextCompiler
from jitsu.models.core import AgentDirective, ContextTarget, TargetResolutionMode
from jitsu.prompts import (
    TAG_CONTEXT_DETAIL,
    TAG_CONTEXT_MANIFEST,
    TAG_INSTRUCTIONS,
    TAG_PRIORITY_RECAP,
    TAG_TASK_SPEC,
)
from jitsu.providers import DirectoryTreeProvider

# Constants for test assertions
_CONCURRENCY_TIMEOUT = 0.03
_EXPECTED_CALL_COUNT_5 = 5
_EXPECTED_CALL_COUNT_2 = 2
_EXPECTED_CALL_COUNT_1 = 1


@pytest.mark.asyncio
async def test_compile_empty_targets() -> None:
    """Test compiling a directive with no context targets."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="do stuff",
        verification_commands=["just check"],
    )
    res = await compiler.compile_directive(directive)
    assert "No context targets." in res
    assert "do stuff" in res


@pytest.mark.asyncio
async def test_compile_with_anti_patterns() -> None:
    """Test compiling a directive that includes anti-patterns."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="do stuff",
        anti_patterns=["Do not use MD5"],
        verification_commands=["just check"],
    )
    res = await compiler.compile_directive(directive)
    assert "## Anti-Patterns" in res
    assert "- Do not use MD5" in res


@pytest.mark.asyncio
async def test_compile_valid_provider() -> None:
    """Test compiling with a successfully resolved target."""
    compiler = ContextCompiler()
    # We use AsyncMock because the compiler expects resolve() to be awaitable
    mock_provider = AsyncMock()
    mock_provider.resolve.return_value = "MOCK_FILE_CONTENT"
    compiler.providers["file"] = mock_provider

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="file",
                target_identifier="test_target",
            )
        ],
        verification_commands=["just check"],
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
    compiler.providers["ast"] = mock_ast
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="file",
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
    compiler.providers["ast"] = mock_ast
    mock_file = AsyncMock()
    mock_file.resolve.return_value = "FILE_CONTENT"
    compiler.providers["file"] = mock_file

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="file",
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
        module_scope=["test"],
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="file",
                target_identifier="README.md",
                resolution_mode=TargetResolutionMode.FULL_SOURCE,
            )
        ],
        verification_commands=["just check"],
    )
    res = await compiler.compile_directive(directive)
    assert TAG_CONTEXT_MANIFEST in res
    assert "- `README.md`: **Full Source** (file)" in res


@pytest.mark.asyncio
async def test_compile_auto_pydantic_trigger() -> None:
    """Test that AUTO mode triggers Pydantic for symbols."""
    compiler = ContextCompiler()
    mock_pydantic = AsyncMock()
    mock_pydantic.resolve.return_value = "SCHEMA_OUTPUT"
    compiler.providers["pydantic"] = mock_pydantic
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="pydantic",
                target_identifier="jitsu.models.core.AgentDirective",
                resolution_mode=TargetResolutionMode.AUTO,
            )
        ],
        verification_commands=["just check"],
    )
    res = await compiler.compile_directive(directive)
    assert "SCHEMA_OUTPUT" in res
    assert "Condensed (JSON Schema)" in res
    mock_pydantic.resolve.assert_called_once_with("jitsu.models.core.AgentDirective")


@pytest.mark.asyncio
async def test_explicit_mode_failure_string_in_manifest() -> None:
    """Test explicit mode when the provider returns a failure string."""
    compiler = ContextCompiler()
    mock_file = AsyncMock()
    mock_file.resolve.return_value = "ERROR: something happened"
    compiler.providers["file"] = mock_file
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="file",
                target_identifier="t",
                resolution_mode=TargetResolutionMode.FULL_SOURCE,
            )
        ],
        verification_commands=["just check"],
    )

    res = await compiler.compile_directive(directive)
    assert "Unknown provider 'file' or resolution failed for 't'." in res


@pytest.mark.asyncio
async def test_compile_explicit_schema_mode() -> None:
    """Test explicit SCHEMA_ONLY mode."""
    compiler = ContextCompiler()
    mock_pydantic = AsyncMock()
    mock_pydantic.resolve.return_value = "SCHEMA_JSON"
    compiler.providers["pydantic"] = mock_pydantic
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="pydantic",
                target_identifier="models.User",
                resolution_mode=TargetResolutionMode.SCHEMA_ONLY,
            )
        ],
        verification_commands=["just check"],
    )
    res = await compiler.compile_directive(directive)
    assert "SCHEMA_JSON" in res
    assert "Condensed (JSON Schema)" in res
    mock_pydantic.resolve.assert_called_once_with("models.User")


@pytest.mark.asyncio
async def test_explicit_mode_missing_provider_failure() -> None:
    """Test explicit mode failure when provider is missing."""
    compiler = ContextCompiler()
    del compiler.providers["ast"]
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="ast",
                target_identifier="t",
                resolution_mode=TargetResolutionMode.STRUCTURE_ONLY,
            )
        ],
        verification_commands=["just check"],
    )
    res = await compiler.compile_directive(directive)
    assert "FAILED" in res


@pytest.mark.asyncio
async def test_unknown_resolution_mode_internal() -> None:
    """Test internal _resolve_explicit with invalid mode."""
    compiler = ContextCompiler()
    res, provider = await compiler.resolve_explicit("target", cast("Any", "INVALID"))
    assert res == ""
    assert provider == "none"


@pytest.mark.asyncio
async def test_compile_with_verification_and_criteria() -> None:
    """Test compiling a directive with verification commands and completion criteria."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="do stuff",
        verification_commands=["just check"],
        completion_criteria=["All tests pass"],
    )
    res = await compiler.compile_directive(directive)
    assert "## Definition of Done" in res
    assert "### Completion Criteria" in res
    assert "- [ ] All tests pass" in res
    assert "### Verification" in res
    assert "You MUST run the following commands" in res
    assert "```bash\njust check\n```" in res


@pytest.mark.asyncio
async def test_compile_no_verification_commands() -> None:
    """Test that empty verification commands show a generic fallback message."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="do stuff",
    )
    res = await compiler.compile_directive(directive)
    assert "## Definition of Done" in res
    assert "### Verification" in res
    assert "No specific verification commands required for this phase." in res
    assert "just verify-fast" not in res


@pytest.mark.asyncio
async def test_compiler_resolve_auto_tree_fallback() -> None:
    """Test that AUTO resolution successfully falls back to the tree provider."""
    compiler = ContextCompiler()
    # We mock the tree provider to return a success string.
    # We pass a target without '.py' or '.' so AST and Pydantic skip it.
    with patch.object(DirectoryTreeProvider, "resolve", return_value="### Directory Tree"):
        res, provider = await compiler.resolve_auto("my_directory", "file")

        assert provider == "tree"
        assert "### Directory Tree" in res


@pytest.mark.asyncio
async def test_compiler_resolve_auto_unknown_preferred() -> None:
    """Test that an unknown preferred provider triggers a warning but continues."""
    compiler = ContextCompiler()
    with patch("jitsu.core.compiler.logger.warning") as mock_logger:
        # Pass a completely unknown provider name
        # It will fail all resolution and drop to the bottom, returning "none"
        await compiler.resolve_auto("fake_target", "hallucinated_provider")

        mock_logger.assert_called_with("Unknown provider '%s' requested", "hallucinated_provider")


@pytest.mark.asyncio
async def test_compiler_resolve_auto_git_diff_as_preferred() -> None:
    """Test that AUTO resolution successfully resolves an unusual preferred provider like git_diff."""
    compiler = ContextCompiler()
    mock_git = AsyncMock()
    mock_git.resolve.return_value = "### Git Diff: HEAD"
    compiler.providers["git_diff"] = mock_git
    res, provider = await compiler.resolve_auto("HEAD", "git_diff")

    assert provider == "git_diff"
    assert "### Git Diff: HEAD" in res
    mock_git.resolve.assert_called_once_with("HEAD")


@pytest.mark.asyncio
async def test_compile_u_curve_ordering() -> None:
    """Test that the compiler follows the exact U-Curve XML ordering."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="do stuff",
    )
    res = await compiler.compile_directive(directive)

    # Assert exact tag presence
    required_tags = [
        TAG_INSTRUCTIONS,
        TAG_CONTEXT_MANIFEST,
        TAG_CONTEXT_DETAIL,
        TAG_PRIORITY_RECAP,
        TAG_TASK_SPEC,
    ]
    for tag in required_tags:
        assert tag in res

    # Assert mathematical ordering (index-based)
    indices = [res.index(tag) for tag in required_tags]
    assert all(indices[i] < indices[i + 1] for i in range(len(indices) - 1))


@pytest.mark.asyncio
async def test_compiler_parallel_resolution() -> None:
    """Test that _resolve_targets processes targets concurrently."""
    compiler = ContextCompiler()

    # Mock providers with artificial delay to verify concurrency
    async def slow_resolve(target: str) -> str:
        await asyncio.sleep(0.01)
        return f"content-{target}"

    mock_provider = AsyncMock()
    mock_provider.resolve.side_effect = slow_resolve
    compiler.providers["file"] = mock_provider

    directive = AgentDirective(
        epic_id="e1",
        phase_id="p1",
        module_scope=["test"],
        instructions="test",
        context_targets=[
            ContextTarget(provider_name="file", target_identifier=f"file{i}.py")
            for i in range(_EXPECTED_CALL_COUNT_5)
        ],
        verification_commands=["just check"],
    )

    # Should complete in ~0.01s (parallel) not ~0.05s (sequential)
    start = asyncio.get_event_loop().time()
    await compiler.compile_directive(directive)
    elapsed = asyncio.get_event_loop().time() - start

    assert elapsed < _CONCURRENCY_TIMEOUT  # Allow small overhead
    assert mock_provider.resolve.call_count == _EXPECTED_CALL_COUNT_5


@pytest.mark.asyncio
async def test_compiler_resolution_cache() -> None:
    """Test that resolve_auto caches successful results."""
    compiler = ContextCompiler()
    mock_provider = AsyncMock()
    mock_provider.resolve.return_value = "cached-content"
    compiler.providers["file"] = mock_provider

    # First call
    res1, _ = await compiler.resolve_auto("target.py", "file")
    assert res1 == "cached-content"
    assert mock_provider.resolve.call_count == _EXPECTED_CALL_COUNT_1

    # Second call with same target should use cache
    res2, _ = await compiler.resolve_auto("target.py", "file")
    assert res2 == "cached-content"
    assert mock_provider.resolve.call_count == _EXPECTED_CALL_COUNT_1

    # Clear cache and verify re-resolution
    compiler.clear_caches()
    _, _ = await compiler.resolve_auto("target.py", "file")
    assert mock_provider.resolve.call_count == _EXPECTED_CALL_COUNT_2


def test_compiler_clear_caches() -> None:
    """Test that clear_caches() empties the resolution cache."""
    compiler = ContextCompiler()
    compiler._resolution_cache[("test", "file", TargetResolutionMode.AUTO)] = "cached"
    assert len(compiler._resolution_cache) == _EXPECTED_CALL_COUNT_1

    compiler.clear_caches()
    assert len(compiler._resolution_cache) == 0


@pytest.mark.asyncio
async def test_compile_required_target_failure() -> None:
    """Test that failed required targets show [FAILED] in output."""
    compiler = ContextCompiler()
    mock_file = AsyncMock()
    mock_file.resolve.return_value = "### [FAILED] File not found"
    compiler.providers["file"] = mock_file

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope=["test"],
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="file",
                target_identifier="missing.py",
                resolution_mode=TargetResolutionMode.FULL_SOURCE,
                is_required=True,  # <-- Key: mark as required
            )
        ],
        verification_commands=["just check"],
    )

    res = await compiler.compile_directive(directive)

    # Verify the [FAILED] marker appears for required targets
    assert "### [FAILED] missing.py" in res
    assert "Unknown provider 'file' or resolution failed for 'missing.py'." in res


@pytest.mark.asyncio
async def test_resolve_targets_empty() -> None:
    """Test that _resolve_targets returns empty lists with no input targets."""
    compiler = ContextCompiler()
    parts, manifest = await compiler._resolve_targets([])
    assert parts == []
    assert manifest == []
