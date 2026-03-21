"""AST file structure and transformation providers for Jitsu."""

from __future__ import annotations

import ast
from typing import Any

from anyio import Path as AsyncPath

from jitsu.providers.base import BaseProvider
from jitsu.utils.logger import get_logger

logger = get_logger(__name__)


class NameTransformer(ast.NodeTransformer):
    """AST transformer for renaming classes and functions."""

    def __init__(self, old_name: str, new_name: str, node_types: tuple[type[ast.AST], ...]) -> None:
        """Initialize with old and new names and target node types."""
        self.old_name = old_name
        self.new_name = new_name
        self.node_types = node_types
        self.modified = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Rename function if it matches the target node type and name."""
        if ast.FunctionDef in self.node_types and node.name == self.old_name:
            node.name = self.new_name
            self.modified = True
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Rename async function if it matches the target node type and name."""
        if ast.FunctionDef in self.node_types and node.name == self.old_name:
            node.name = self.new_name
            self.modified = True
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """Rename class if it matches the target node type and name."""
        if ast.ClassDef in self.node_types and node.name == self.old_name:
            node.name = self.new_name
            self.modified = True
        self.generic_visit(node)
        return node


class ParameterTransformer(ast.NodeTransformer):
    """AST transformer for adding parameters to functions."""

    def __init__(
        self,
        func_name: str,
        param_name: str,
        default_value: Any = None,  # noqa: ANN401
    ) -> None:
        """Initialize with target function name and new parameter details."""
        self.func_name = func_name
        self.param_name = param_name
        self.default_value = default_value
        self.modified = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Add parameter to function if name matches."""
        if node.name == self.func_name:
            self._add_param(node)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Add parameter to async function if name matches."""
        if node.name == self.func_name:
            self._add_param(node)
        self.generic_visit(node)
        return node

    def _add_param(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Add a parameter to a function node."""
        # Detect if parameter already exists across all argument types
        all_args = [arg.arg for arg in node.args.args]
        all_args.extend(arg.arg for arg in node.args.posonlyargs)
        all_args.extend(arg.arg for arg in node.args.kwonlyargs)
        if node.args.vararg:
            all_args.append(node.args.vararg.arg)
        if node.args.kwarg:
            all_args.append(node.args.kwarg.arg)

        if self.param_name in all_args:
            return

        new_arg = ast.arg(arg=self.param_name, annotation=None)

        if self.default_value is not None:
            # Append as keyword-only argument with default for safety
            node.args.kwonlyargs.append(new_arg)
            node.args.kw_defaults.append(ast.Constant(value=self.default_value))
        else:
            # Append as regular positional argument
            node.args.args.append(new_arg)

        self.modified = True


class ASTTransformer:
    """Provides safe Python code mutations using AST manipulation."""

    async def _parse_source(self, file_path: str) -> ast.AST:
        """Read and parse the source file."""
        path = AsyncPath(file_path)
        source = await path.read_text(encoding="utf-8")
        return ast.parse(source, filename=file_path)

    async def _validate_and_write(self, file_path: str, tree: ast.AST) -> None:
        """Unparse AST, validate syntax, and write back to disk."""
        new_source = ast.unparse(tree)
        # Ensure the generated code is syntactically valid
        ast.parse(new_source)
        path = AsyncPath(file_path)
        await path.write_text(new_source, encoding="utf-8")

    async def rename_function(self, file_path: str, old_name: str, new_name: str) -> None:
        """
        Rename a function or method in the specified file.

        Args:
            file_path: Path to the target Python file.
            old_name: Current name of the function.
            new_name: Desired new name.

        """
        tree = await self._parse_source(file_path)
        transformer = NameTransformer(old_name, new_name, (ast.FunctionDef,))
        transformer.visit(tree)
        if transformer.modified:
            await self._validate_and_write(file_path, tree)
        else:
            msg = f"Function '{old_name}' not found in {file_path}."
            raise ValueError(msg)

    async def rename_class(self, file_path: str, old_name: str, new_name: str) -> None:
        """
        Rename a class in the specified file.

        Args:
            file_path: Path to the target Python file.
            old_name: Current name of the class.
            new_name: Desired new name.

        """
        tree = await self._parse_source(file_path)
        transformer = NameTransformer(old_name, new_name, (ast.ClassDef,))
        transformer.visit(tree)
        if transformer.modified:
            await self._validate_and_write(file_path, tree)
        else:
            msg = f"Class '{old_name}' not found in {file_path}."
            raise ValueError(msg)

    async def add_parameter(
        self,
        file_path: str,
        func_name: str,
        param_name: str,
        default_value: Any = None,  # noqa: ANN401
    ) -> None:
        """
        Add a new parameter to a function's signature.

        Args:
            file_path: Path to the target Python file.
            func_name: Name of the function to modify.
            param_name: Name of the new parameter.
            default_value: Optional default value. If provided, adds as keyword-only.

        """
        tree = await self._parse_source(file_path)
        transformer = ParameterTransformer(func_name, param_name, default_value)
        transformer.visit(tree)
        if transformer.modified:
            await self._validate_and_write(file_path, tree)
        else:
            msg = f"Function '{func_name}' not found or parameter already exists in {file_path}."
            raise ValueError(msg)


class ASTProvider(BaseProvider):
    """
    Provides a structural skeleton of a Python file.

    Extracts classes, methods, functions, and their docstrings
    using the built-in ast module to save token space.
    """

    @property
    def name(self) -> str:
        """The unique name of this provider."""
        return "ast"

    def _format_function_def(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, indent: int = 0
    ) -> list[str]:
        """Format a function or method definition."""
        lines: list[str] = []
        prefix = " " * indent
        args = ast.unparse(node.args)

        func_type = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        lines.append(f"{prefix}{func_type} {node.name}({args}):")

        doc = ast.get_docstring(node)
        if doc:
            lines.append(f'{prefix}    """{doc}"""')
        else:
            lines.append(f"{prefix}    ...")

        return lines

    def _format_class_def(self, node: ast.ClassDef) -> list[str]:
        """Format a class definition and its methods."""
        lines: list[str] = []
        lines.append(f"class {node.name}:")

        doc = ast.get_docstring(node)
        if doc:
            lines.append(f'    """{doc}"""')

        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                lines.extend(self._format_function_def(item, indent=4))

        lines.append("")
        return lines

    async def resolve(self, target: str) -> str:
        """
        Parse a Python file and return its structural outline.

        Args:
            target: The file path to parse (e.g., 'src/main.py').

        Returns:
            str: A formatted Markdown block with the file's AST skeleton.

        """
        path = AsyncPath(target)

        # ASYNC240 Fix: Await the async path checking
        if not await path.is_file():
            return f"### [FAILED] AST Provider: {target}\n**ERROR:** File not found or not a valid file path."

        try:
            # ASYNC240 Fix: Await non-blocking file read
            source = await path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=path.name)
        except SyntaxError as e:
            # TRY400 Fix: Use exception instead of error
            logger.exception("Syntax error parsing %s", target)
            return f"### [FAILED] AST Provider: {target}\n**ERROR:** Syntax error in file: {e}"
        except Exception as e:
            logger.exception("Unexpected error parsing %s", target)
            return f"### [FAILED] AST Provider: {target}\n**ERROR:** Unexpected error: {e}"

        # C901 / PLR0912 Fix: Complexity drastically reduced by using helpers
        lines: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                lines.extend(self._format_class_def(node))
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                lines.extend(self._format_function_def(node))
                lines.append("")

        skeleton = "\n".join(lines).strip()
        if not skeleton:
            skeleton = "# No structural elements (classes/functions) found."

        return f"### AST Structural Outline: {target}\n```python\n{skeleton}\n```"
