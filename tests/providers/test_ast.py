"""Tests for the AST provider."""

from pathlib import Path
from unittest.mock import patch

import pytest

from jitsu.providers.ast import ASTProvider


@pytest.mark.asyncio
async def test_ast_provider_success(tmp_path: Path) -> None:
    """Test successful extraction of a Python file structure."""
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        '''
class MyClass:
    """Class docstring."""
    def my_method(self, arg1: int):
        """Method docstring."""
        pass

class UndocumentedClass:
    def undocumented_method(self):
        pass

async def my_async_function():
    pass

def my_function(x: str="default"):
    """Function docstring."""
    return x
        ''',
        encoding="utf-8",
    )

    provider = ASTProvider()
    assert provider.name == "ast"
    res = await provider.resolve(str(file_path))

    assert "### AST Structural Outline:" in res
    assert "class MyClass:" in res
    assert '"""Class docstring."""' in res
    assert "def my_method(self, arg1: int):" in res
    assert "class UndocumentedClass:" in res
    assert "def undocumented_method(self):" in res
    assert "async def my_async_function():" in res
    assert "def my_function(x: str='default'):" in res
    assert "..." in res


@pytest.mark.asyncio
async def test_ast_provider_empty_structure(tmp_path: Path) -> None:
    """Test resolution of a file with no classes or functions."""
    file_path = tmp_path / "empty.py"
    file_path.write_text("x = 10\ny = 20\n", encoding="utf-8")

    provider = ASTProvider()
    res = await provider.resolve(str(file_path))
    assert "No structural elements (classes/functions) found." in res


@pytest.mark.asyncio
async def test_ast_provider_file_not_found() -> None:
    """Test resolution when the target file does not exist."""
    provider = ASTProvider()
    res = await provider.resolve("non_existent_file.py")
    assert "**ERROR:** File not found" in res


@pytest.mark.asyncio
async def test_ast_provider_syntax_error(tmp_path: Path) -> None:
    """Test resolution when the file contains invalid Python syntax."""
    file_path = tmp_path / "invalid.py"
    file_path.write_text("class Def Invalid Syntax::::", encoding="utf-8")

    provider = ASTProvider()
    res = await provider.resolve(str(file_path))
    assert "**ERROR:** Syntax error in file" in res


@pytest.mark.asyncio
async def test_ast_provider_unexpected_error(tmp_path: Path) -> None:
    """Test resolution when an unexpected error occurs during read."""
    file_path = tmp_path / "error.py"
    file_path.write_text("class MyClass:\n    pass\n", encoding="utf-8")

    provider = ASTProvider()
    with patch("anyio.Path.read_text", side_effect=RuntimeError("Disk failure!")):
        res = await provider.resolve(str(file_path))
        assert "**ERROR:** Unexpected error: Disk failure!" in res
