"""Unit tests for the MarkdownASTProvider."""

from pathlib import Path
from unittest.mock import patch

import pytest

from jitsu.providers.markdown import MarkdownASTProvider


@pytest.mark.asyncio
async def test_markdown_provider_name() -> None:
    """Test the provider name."""
    provider = MarkdownASTProvider(Path.cwd())
    assert provider.name == "markdown_ast"


@pytest.mark.asyncio
async def test_markdown_provider_resolve_structural_elements(tmp_path: Path) -> None:
    """Test resolving a markdown file, collecting only headings and code delimiters."""
    provider = MarkdownASTProvider(tmp_path)
    md_content = (
        "# Title\n"
        "Some description text.\n"
        "## Section 1\n"
        "Inside section 1 text.\n"
        "```python\n"
        "def hello():\n"
        "    print('world')\n"
        "```\n"
        "### Subsection\n"
        "More text.\n"
        "#### Not a heading because no space\n"
        "Actually, let's test the space rule specifically:\n"
        "#NoSpaceHeading\n"
        "  # Indented heading (should we support this? instructions say 'start with')\n"
        "````\n"
        "Four backticks\n"
        "````\n"
        "```\n"
        "End of block\n"
        "```\n"
    )
    md_file = tmp_path / "test.md"
    md_file.write_text(md_content, encoding="utf-8")

    result = await provider.resolve("test.md")

    # Should be present
    assert "# Title" in result
    assert "## Section 1" in result
    assert "### Subsection" in result
    assert "```python" in result
    assert "```" in result

    # Should be ignored
    assert "Some description text." not in result
    assert "Inside section 1 text." not in result
    assert "def hello():" not in result
    assert "More text." not in result
    assert "#NoSpaceHeading" not in result
    assert "Four backticks" not in result
    assert "````" not in result


@pytest.mark.asyncio
async def test_markdown_provider_empty_file(tmp_path: Path) -> None:
    """Test resolving an empty markdown file."""
    provider = MarkdownASTProvider(tmp_path)
    md_file = tmp_path / "empty.md"
    md_file.write_text("", encoding="utf-8")

    result = await provider.resolve("empty.md")

    assert "No headings or code blocks found" in result


@pytest.mark.asyncio
async def test_markdown_provider_missing_file(tmp_path: Path) -> None:
    """Test resolving a missing file."""
    provider = MarkdownASTProvider(tmp_path)

    result = await provider.resolve("missing.md")

    assert "[FAILED]" in result
    assert "File not found" in result


@pytest.mark.asyncio
async def test_markdown_provider_read_method(tmp_path: Path) -> None:
    """Test the explicit read() method returns a list of lines."""
    provider = MarkdownASTProvider(tmp_path)
    md_content = "# H1\nText\n```js\n```"
    md_file = tmp_path / "read_test.md"
    md_file.write_text(md_content, encoding="utf-8")

    lines = provider.read("read_test.md")

    assert lines == ["# H1", "```js", "```"]


@pytest.mark.asyncio
async def test_markdown_provider_directory_target(tmp_path: Path) -> None:
    """Test resolving a directory instead of a file."""
    provider = MarkdownASTProvider(tmp_path)
    dir_path = tmp_path / "subdir"
    dir_path.mkdir()

    result = await provider.resolve("subdir")

    assert "No headings or code blocks found" in result


@pytest.mark.asyncio
async def test_markdown_provider_read_exception(tmp_path: Path) -> None:
    """Test handling of read exceptions."""
    provider = MarkdownASTProvider(tmp_path)
    md_file = tmp_path / "error.md"
    md_file.write_text("# Title", encoding="utf-8")

    with (
        patch("pathlib.Path.open", side_effect=PermissionError("Mock Error")),
    ):
        lines = provider.read("error.md")

    assert lines == []


@pytest.mark.asyncio
async def test_markdown_provider_whitespace_file(tmp_path: Path) -> None:
    """Test resolving a file with only whitespace."""
    provider = MarkdownASTProvider(tmp_path)
    md_file = tmp_path / "whitespace.md"
    md_file.write_text("   \n  \t  \n", encoding="utf-8")

    result = await provider.resolve("whitespace.md")

    assert "No headings or code blocks found" in result
