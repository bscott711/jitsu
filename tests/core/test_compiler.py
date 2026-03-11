"""Tests for the Context Compiler engine."""

from unittest.mock import AsyncMock, patch

import pytest

from jitsu.core.compiler import ContextCompiler
from jitsu.models.core import AgentDirective, ContextTarget, TargetResolutionMode
from jitsu.providers import DirectoryTreeProvider


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
async def test_compile_valid_provider() -> None:
    """Test compiling with a successfully resolved target."""
    compiler = ContextCompiler()

    # We use AsyncMock because the compiler expects resolve() to be awaitable
    mock_provider = AsyncMock()
    mock_provider.resolve.return_value = "MOCK_FILE_CONTENT"
    compiler._providers["file"] = mock_provider  # noqa: SLF001

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="file",
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
    compiler._providers["ast"] = mock_ast  # noqa: SLF001

    mock_file = AsyncMock()
    mock_file.resolve.return_value = "FILE_CONTENT"
    compiler._providers["file"] = mock_file  # noqa: SLF001

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
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
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="file",
                target_identifier="README.md",
                resolution_mode=TargetResolutionMode.FULL_SOURCE,
            )
        ],
    )
    res = await compiler.compile_directive(directive)
    assert "## Compiled Context Manifest" in res
    assert "- `README.md`: **Full Source** (file)" in res


@pytest.mark.asyncio
async def test_compile_auto_pydantic_trigger() -> None:
    """Test that AUTO mode triggers Pydantic for symbols."""
    compiler = ContextCompiler()
    mock_pydantic = AsyncMock()
    mock_pydantic.resolve.return_value = "SCHEMA_OUTPUT"
    compiler._providers["pydantic"] = mock_pydantic  # noqa: SLF001

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="pydantic",
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
    compiler._providers["file"] = mock_file  # noqa: SLF001

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="file",
                target_identifier="t",
                resolution_mode=TargetResolutionMode.FULL_SOURCE,
            )
        ],
    )

    res = await compiler.compile_directive(directive)
    assert "Unknown provider 'file' or resolution failed for 't'." in res


@pytest.mark.asyncio
async def test_compile_explicit_schema_mode() -> None:
    """Test explicit SCHEMA_ONLY mode."""
    compiler = ContextCompiler()
    mock_pydantic = AsyncMock()
    mock_pydantic.resolve.return_value = "SCHEMA_JSON"
    compiler._providers["pydantic"] = mock_pydantic  # noqa: SLF001

    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="test",
        context_targets=[
            ContextTarget(
                provider_name="pydantic",
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
                provider_name="ast",
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


@pytest.mark.asyncio
async def test_compile_with_verification_and_criteria() -> None:
    """Test compiling a directive with verification commands and completion criteria."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="do stuff",
        verification_commands=["just verify"],
        completion_criteria=["All tests pass"],
    )
    res = await compiler.compile_directive(directive)
    assert "## Definition of Done" in res
    assert "### Completion Criteria" in res
    assert "- [ ] All tests pass" in res
    assert "### Verification" in res
    assert "You MUST run the following commands" in res
    assert "```bash\njust verify\n```" in res


@pytest.mark.asyncio
async def test_compile_no_verification_commands() -> None:
    """Test that empty verification commands show a generic fallback message."""
    compiler = ContextCompiler()
    directive = AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="test",
        instructions="do stuff",
    )
    res = await compiler.compile_directive(directive)
    assert "## Definition of Done" in res
    assert "### Verification" in res
    assert "*No specific verification commands required for this phase.*" in res
    assert "just verify-fast" not in res


@pytest.mark.asyncio
async def test_compiler_resolve_auto_tree_fallback() -> None:
    """Test that AUTO resolution successfully falls back to the tree provider."""
    compiler = ContextCompiler()

    # We mock the tree provider to return a success string.
    # We pass a target without '.py' or '.' so AST and Pydantic skip it.
    with patch.object(DirectoryTreeProvider, "resolve", return_value="### Directory Tree"):
        res, provider = await compiler._resolve_auto("my_directory", "file")  # noqa: SLF001

        assert provider == "tree"
        assert "### Directory Tree" in res


@pytest.mark.asyncio
async def test_compiler_resolve_auto_unknown_preferred() -> None:
    """Test that an unknown preferred provider triggers a warning but continues."""
    compiler = ContextCompiler()

    with patch("jitsu.core.compiler.logger.warning") as mock_logger:
        # Pass a completely unknown provider name
        # It will fail all resolution and drop to the bottom, returning "none"
        await compiler._resolve_auto("fake_target", "hallucinated_provider")  # noqa: SLF001

        mock_logger.assert_called_with("Unknown provider '%s' requested", "hallucinated_provider")


@pytest.mark.asyncio
async def test_compiler_resolve_auto_git_diff_as_preferred() -> None:
    """Test that AUTO resolution successfully resolves an unusual preferred provider like git_diff."""
    compiler = ContextCompiler()
    mock_git = AsyncMock()
    mock_git.resolve.return_value = "### Git Diff: HEAD"
    compiler._providers["git_diff"] = mock_git  # noqa: SLF001

    res, provider = await compiler._resolve_auto("HEAD", "git_diff")  # noqa: SLF001

    assert provider == "git_diff"
    assert "### Git Diff: HEAD" in res
    mock_git.resolve.assert_called_once_with("HEAD")
