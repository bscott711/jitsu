"""Tests for AST-based tool handlers."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from mcp import types

from jitsu.core.compiler import ContextCompiler
from jitsu.core.state import JitsuStateManager
from jitsu.providers.registry import ProviderRegistry
from jitsu.server.handlers import ToolHandlers


@pytest.fixture
def handlers() -> ToolHandlers:
    """Fixture for ToolHandlers."""
    state = JitsuStateManager()
    registry = ProviderRegistry  # It's a dict
    compiler = ContextCompiler(registry)
    return ToolHandlers(state, compiler)


class TestAstRenameFunctionHandler:
    """Test suite for jitsu_ast_rename_function handler."""

    @pytest.mark.asyncio
    async def test_handle_ast_rename_function_success(self, handlers: ToolHandlers) -> None:
        """Test successful function rename."""
        args = {
            "file_path": "test.py",
            "old_name": "old_func",
            "new_name": "new_func",
        }

        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.rename_function = AsyncMock()

            result = await handlers.handle_ast_rename_function(args)

            assert len(result) == 1
            assert isinstance(result[0], types.TextContent)
            data = json.loads(result[0].text)
            assert data["status"] == "success"
            assert "Renamed function old_func to new_func" in data["message"]
            mock_instance.rename_function.assert_called_once_with("test.py", "old_func", "new_func")

    @pytest.mark.asyncio
    async def test_handle_ast_rename_function_not_found(self, handlers: ToolHandlers) -> None:
        """Test function not found error."""
        args = {
            "file_path": "test.py",
            "old_name": "missing",
            "new_name": "new",
        }

        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.rename_function = AsyncMock(
                side_effect=ValueError("Function 'missing' not found")
            )

            result = await handlers.handle_ast_rename_function(args)

            data = json.loads(result[0].text)
            assert data["status"] == "error"
            assert "Function 'missing' not found" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_ast_rename_function_file_not_found(self, handlers: ToolHandlers) -> None:
        """Test file not found error."""
        args = {"file_path": "missing.py", "old_name": "f", "new_name": "g"}

        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.rename_function = AsyncMock(side_effect=FileNotFoundError())

            result = await handlers.handle_ast_rename_function(args)

            data = json.loads(result[0].text)
            assert data["status"] == "error"
            assert "File not found" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_ast_rename_function_syntax_error(self, handlers: ToolHandlers) -> None:
        """Test syntax error handling."""
        args = {"file_path": "bad.py", "old_name": "f", "new_name": "g"}

        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.rename_function = AsyncMock(side_effect=SyntaxError("invalid syntax"))

            result = await handlers.handle_ast_rename_function(args)

            data = json.loads(result[0].text)
            assert data["status"] == "error"
            assert "Invalid Python syntax" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_ast_rename_function_generic_exception(
        self, handlers: ToolHandlers
    ) -> None:
        """Test generic exception handling."""
        args = {"file_path": "test.py", "old_name": "f", "new_name": "g"}

        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.rename_function = AsyncMock(side_effect=RuntimeError("Disk failure"))

            result = await handlers.handle_ast_rename_function(args)

            data = json.loads(result[0].text)
            assert data["status"] == "error"
            assert "Disk failure" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_ast_rename_function_missing_args(self, handlers: ToolHandlers) -> None:
        """Test missing arguments."""
        result = await handlers.handle_ast_rename_function({})
        data = json.loads(result[0].text)
        assert data["status"] == "error"
        assert "Missing arguments" in data["message"]


class TestAstRenameClassHandler:
    """Test suite for jitsu_ast_rename_class handler."""

    @pytest.mark.asyncio
    async def test_handle_ast_rename_class_success(self, handlers: ToolHandlers) -> None:
        """Test successful class rename."""
        args = {"file_path": "test.py", "old_name": "OldClass", "new_name": "NewClass"}

        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.rename_class = AsyncMock()

            result = await handlers.handle_ast_rename_class(args)

            data = json.loads(result[0].text)
            assert data["status"] == "success"
            assert "Renamed class OldClass to NewClass" in data["message"]
            mock_instance.rename_class.assert_called_once_with("test.py", "OldClass", "NewClass")

    @pytest.mark.asyncio
    async def test_handle_ast_rename_class_not_found(self, handlers: ToolHandlers) -> None:
        """Test class not found error."""
        args = {"file_path": "test.py", "old_name": "missing", "new_name": "new"}

        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.rename_class = AsyncMock(
                side_effect=ValueError("Class 'missing' not found")
            )

            result = await handlers.handle_ast_rename_class(args)

            data = json.loads(result[0].text)
            assert data["status"] == "error"
            assert "Class 'missing' not found" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_ast_rename_class_file_not_found(self, handlers: ToolHandlers) -> None:
        """Test file not found error for class rename."""
        args = {"file_path": "missing.py", "old_name": "C", "new_name": "D"}
        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.rename_class = AsyncMock(side_effect=FileNotFoundError())
            result = await handlers.handle_ast_rename_class(args)
            data = json.loads(result[0].text)
            assert data["status"] == "error"
            assert "File not found" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_ast_rename_class_syntax_error(self, handlers: ToolHandlers) -> None:
        """Test syntax error for class rename."""
        args = {"file_path": "bad.py", "old_name": "C", "new_name": "D"}
        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.rename_class = AsyncMock(side_effect=SyntaxError("bad syntax"))
            result = await handlers.handle_ast_rename_class(args)
            data = json.loads(result[0].text)
            assert data["status"] == "error"
            assert "Invalid Python syntax" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_ast_rename_class_generic_exception(self, handlers: ToolHandlers) -> None:
        """Test generic exception for class rename."""
        args = {"file_path": "test.py", "old_name": "C", "new_name": "D"}
        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.rename_class = AsyncMock(side_effect=RuntimeError("Fail"))
            result = await handlers.handle_ast_rename_class(args)
            data = json.loads(result[0].text)
            assert data["status"] == "error"
            assert "Fail" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_ast_rename_class_missing_args(self, handlers: ToolHandlers) -> None:
        """Test missing arguments for class rename."""
        result = await handlers.handle_ast_rename_class({})
        data = json.loads(result[0].text)
        assert data["status"] == "error"
        assert "Missing arguments" in data["message"]


class TestAstAddParameterHandler:
    """Test suite for jitsu_ast_add_parameter handler."""

    @pytest.mark.asyncio
    async def test_handle_ast_add_parameter_file_not_found(self, handlers: ToolHandlers) -> None:
        """Test file not found for add parameter."""
        args = {"file_path": "missing.py", "func_name": "f", "param_name": "p"}
        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.add_parameter = AsyncMock(side_effect=FileNotFoundError())
            result = await handlers.handle_ast_add_parameter(args)
            data = json.loads(result[0].text)
            assert data["status"] == "error"
            assert "File not found" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_ast_add_parameter_syntax_error(self, handlers: ToolHandlers) -> None:
        """Test syntax error for add parameter."""
        args = {"file_path": "bad.py", "func_name": "f", "param_name": "p"}
        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.add_parameter = AsyncMock(side_effect=SyntaxError("bad"))
            result = await handlers.handle_ast_add_parameter(args)
            data = json.loads(result[0].text)
            assert data["status"] == "error"
            assert "Invalid Python syntax" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_ast_add_parameter_generic_exception(self, handlers: ToolHandlers) -> None:
        """Test generic exception for add parameter."""
        args = {"file_path": "test.py", "func_name": "f", "param_name": "p"}
        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.add_parameter = AsyncMock(side_effect=RuntimeError("Fail"))
            result = await handlers.handle_ast_add_parameter(args)
            data = json.loads(result[0].text)
            assert data["status"] == "error"
            assert "Fail" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_ast_add_parameter_success(self, handlers: ToolHandlers) -> None:
        """Test successful parameter addition."""
        args = {
            "file_path": "test.py",
            "func_name": "my_func",
            "param_name": "new_p",
            "default_value": "42",
        }

        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.add_parameter = AsyncMock()

            result = await handlers.handle_ast_add_parameter(args)

            data = json.loads(result[0].text)
            assert data["status"] == "success"
            assert "Successfully added parameter 'new_p' to function 'my_func'" in data["message"]
            # Verify literal_eval turned "42" into 42
            mock_instance.add_parameter.assert_called_once_with("test.py", "my_func", "new_p", 42)

    @pytest.mark.asyncio
    async def test_handle_ast_add_parameter_string_success(self, handlers: ToolHandlers) -> None:
        """Test successful parameter addition with string default."""
        args = {
            "file_path": "test.py",
            "func_name": "my_func",
            "param_name": "new_p",
            "default_value": "'default'",
        }

        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.add_parameter = AsyncMock()

            result = await handlers.handle_ast_add_parameter(args)

            data = json.loads(result[0].text)
            assert data["status"] == "success"
            # Verify literal_eval turned "'default'" into 'default'
            mock_instance.add_parameter.assert_called_once_with(
                "test.py", "my_func", "new_p", "default"
            )

    @pytest.mark.asyncio
    async def test_handle_ast_add_parameter_error(self, handlers: ToolHandlers) -> None:
        """Test parameter addition error."""
        args = {"file_path": "test.py", "func_name": "missing", "param_name": "p"}

        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.add_parameter = AsyncMock(side_effect=ValueError("Function not found"))

            result = await handlers.handle_ast_add_parameter(args)

            data = json.loads(result[0].text)
            assert data["status"] == "error"
            assert "Function not found" in data["message"]

    @pytest.mark.asyncio
    async def test_handle_ast_add_parameter_non_literal_default(
        self, handlers: ToolHandlers
    ) -> None:
        """Test parameter addition with a non-literal default value string."""
        args = {
            "file_path": "test.py",
            "func_name": "my_func",
            "param_name": "new_p",
            "default_value": "os.path.join('a', 'b')",
        }

        with patch("jitsu.server.handlers.ASTTransformer") as mock_transformer:
            mock_instance = mock_transformer.return_value
            mock_instance.add_parameter = AsyncMock()

            result = await handlers.handle_ast_add_parameter(args)

            data = json.loads(result[0].text)
            assert data["status"] == "success"
            # Verify literal_eval fallback to raw string
            mock_instance.add_parameter.assert_called_once_with(
                "test.py", "my_func", "new_p", "os.path.join('a', 'b')"
            )

    @pytest.mark.asyncio
    async def test_handle_ast_add_parameter_missing_args(self, handlers: ToolHandlers) -> None:
        """Test missing arguments."""
        result = await handlers.handle_ast_add_parameter({})
        data = json.loads(result[0].text)
        assert data["status"] == "error"
        assert "Missing arguments" in data["message"]
