"""AST file structure provider for Jitsu."""

import ast

from anyio import Path as AsyncPath

from jitsu.providers.base import BaseProvider
from jitsu.utils.logger import get_logger

logger = get_logger(__name__)


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
        lines: list[str] = []  # <-- Add explicit type hint here
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
        lines: list[str] = []  # <-- Add explicit type hint here
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
