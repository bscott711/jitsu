"""Tests for the ASTTransformer class."""

import ast
from pathlib import Path

import pytest

from jitsu.providers.ast import ASTTransformer


@pytest.fixture
def transformer() -> ASTTransformer:
    """Fixture for ASTTransformer."""
    return ASTTransformer()


@pytest.mark.asyncio
async def test_rename_function(tmp_path: Path, transformer: ASTTransformer) -> None:
    """Test renaming a function."""
    file_path = tmp_path / "test.py"
    file_path.write_text("def old_func():\n    return 42\n", encoding="utf-8")

    await transformer.rename_function(str(file_path), "old_func", "new_func")

    content = file_path.read_text()
    assert "def new_func():" in content
    assert "def old_func():" not in content
    # Verify it still parses
    ast.parse(content)


@pytest.mark.asyncio
async def test_rename_async_function(tmp_path: Path, transformer: ASTTransformer) -> None:
    """Test renaming an async function."""
    file_path = tmp_path / "test_async.py"
    file_path.write_text("async def old_async():\n    pass\n", encoding="utf-8")

    await transformer.rename_function(str(file_path), "old_async", "new_async")

    content = file_path.read_text()
    assert "async def new_async():" in content
    # Verify it still parses
    ast.parse(content)


@pytest.mark.asyncio
async def test_rename_method(tmp_path: Path, transformer: ASTTransformer) -> None:
    """Test renaming a method inside a class."""
    file_path = tmp_path / "test_class.py"
    file_path.write_text(
        "class MyClass:\n    def old_method(self):\n        pass\n", encoding="utf-8"
    )

    await transformer.rename_function(str(file_path), "old_method", "new_method")

    content = file_path.read_text()
    assert "def new_method(self):" in content
    # Verify it still parses
    ast.parse(content)


@pytest.mark.asyncio
async def test_rename_class(tmp_path: Path, transformer: ASTTransformer) -> None:
    """Test renaming a class."""
    file_path = tmp_path / "test_class_rename.py"
    file_path.write_text("class OldClass:\n    pass\n", encoding="utf-8")

    await transformer.rename_class(str(file_path), "OldClass", "NewClass")

    content = file_path.read_text()
    assert "class NewClass:" in content
    # Verify it still parses
    ast.parse(content)


@pytest.mark.asyncio
async def test_add_parameter_positional(tmp_path: Path, transformer: ASTTransformer) -> None:
    """Test adding a positional parameter."""
    file_path = tmp_path / "test_param.py"
    file_path.write_text("def my_func(a):\n    return a\n", encoding="utf-8")

    await transformer.add_parameter(str(file_path), "my_func", "b")

    content = file_path.read_text()
    assert "def my_func(a, b):" in content
    # Verify it still parses
    ast.parse(content)


@pytest.mark.asyncio
async def test_add_parameter_with_default(tmp_path: Path, transformer: ASTTransformer) -> None:
    """Test adding a parameter with a default value (becomes keyword-only)."""
    file_path = tmp_path / "test_param_default.py"
    file_path.write_text("def my_func(a):\n    return a\n", encoding="utf-8")

    await transformer.add_parameter(str(file_path), "my_func", "b", default_value=10)

    content = file_path.read_text()
    # ast.unparse might format this as def my_func(a, *, b=10):
    assert "def my_func(a, *, b=10):" in content
    # Verify it still parses
    ast.parse(content)


@pytest.mark.asyncio
async def test_add_duplicate_parameter(tmp_path: Path, transformer: ASTTransformer) -> None:
    """Test adding a parameter that already exists."""
    file_path = tmp_path / "test_dup.py"
    source = "def my_func(a, b):\n    return a + b\n"
    file_path.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match="already exists"):
        await transformer.add_parameter(str(file_path), "my_func", "a")

    content = file_path.read_text()
    assert content == source


@pytest.mark.asyncio
async def test_transformer_no_match(tmp_path: Path, transformer: ASTTransformer) -> None:
    """Test that no changes are made if no match is found."""
    file_path = tmp_path / "no_match.py"
    source = "def other_func():\n    pass\n"
    file_path.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match="not found"):
        await transformer.rename_function(str(file_path), "missing", "found")

    content = file_path.read_text()
    assert content == source


@pytest.mark.asyncio
async def test_transformer_invalid_syntax(tmp_path: Path, transformer: ASTTransformer) -> None:
    """Test handling of invalid syntax in target file."""
    file_path = tmp_path / "invalid.py"
    file_path.write_text("class Def Invalid!", encoding="utf-8")

    with pytest.raises(SyntaxError):
        await transformer.rename_class(str(file_path), "Old", "New")


@pytest.mark.asyncio
async def test_add_parameter_to_async(tmp_path: Path, transformer: ASTTransformer) -> None:
    """Test adding a parameter to an async function."""
    file_path = tmp_path / "test_async_param.py"
    file_path.write_text("async def my_async(x):\n    pass\n", encoding="utf-8")

    await transformer.add_parameter(str(file_path), "my_async", "y")

    content = file_path.read_text()
    assert "async def my_async(x, y):" in content
    # Verify it still parses
    ast.parse(content)


@pytest.mark.asyncio
async def test_rename_function_nested(tmp_path: Path, transformer: ASTTransformer) -> None:
    """Test renaming a nested function."""
    file_path = tmp_path / "test_nested.py"
    file_path.write_text(
        "def outer():\n    def inner():\n        pass\n    return inner\n", encoding="utf-8"
    )

    await transformer.rename_function(str(file_path), "inner", "renamed_inner")

    content = file_path.read_text()
    assert "def renamed_inner():" in content
    # Verify it still parses
    ast.parse(content)


@pytest.mark.asyncio
async def test_add_parameter_with_varargs_kwargs(
    tmp_path: Path, transformer: ASTTransformer
) -> None:
    """Test adding a parameter to a function with *args and **kwargs."""
    file_path = tmp_path / "test_var.py"
    file_path.write_text("def my_func(*args, **kwargs):\n    pass\n", encoding="utf-8")

    await transformer.add_parameter(str(file_path), "my_func", "new_p")

    content = file_path.read_text()
    assert "new_p" in content
    # Verify it still parses
    ast.parse(content)


@pytest.mark.asyncio
async def test_add_parameter_duplicate_in_varargs(
    tmp_path: Path, transformer: ASTTransformer
) -> None:
    """Test adding a parameter that is already the name of the *args or **kwargs."""
    file_path = tmp_path / "test_dup_var.py"
    file_path.write_text("def my_func(*args, **kwargs):\n    pass\n", encoding="utf-8")

    with pytest.raises(ValueError, match="already exists"):
        await transformer.add_parameter(str(file_path), "my_func", "args")

    content = file_path.read_text()
    assert (
        content.strip() == "def my_func(*args, **kwargs):\n    pass"
        or content.strip() == "def my_func(*args, **kwargs):\n    pass\n"
    )


@pytest.mark.asyncio
async def test_rename_class_not_found(tmp_path: Path, transformer: ASTTransformer) -> None:
    """Test renaming a class that doesn't exist."""
    file_path = tmp_path / "test_no_class.py"
    file_path.write_text("def f(): pass\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not found"):
        await transformer.rename_class(str(file_path), "MissingClass", "NewClass")

    content = file_path.read_text()
    assert content.strip() == "def f(): pass"
