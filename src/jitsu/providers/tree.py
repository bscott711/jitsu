"""Directory tree context provider for Jitsu."""

import typing
from pathlib import Path

from jitsu.providers.base import BaseProvider


class DirectoryTreeProvider(BaseProvider):
    """
    A Context Provider that returns a visual directory tree structure.

    This provider uses recursion to build a Markdown-formatted tree representation
    of a directory's contents, while filtering out common build/version control
    artifacts to minimize token usage.
    """

    # Directories to ignore
    EXCLUDE: typing.ClassVar[set[str]] = {
        ".git",
        "__pycache__",
        ".venv",
        ".pytest_cache",
        "node_modules",
    }

    @property
    def name(self) -> str:
        """The unique name of this provider."""
        return "tree"

    async def resolve(self, target: str) -> str:
        """
        Resolve the directory path and return its tree structure.

        Args:
            target: The relative path to the directory from the project root.

        Returns:
            str: A Markdown-formatted string containing the directory tree.

        """
        target_str = str(target).strip()
        # Handle the case where target is empty or "."
        target_path = self.workspace_root / target_str

        if not target_path.exists():
            return f"ERROR: Directory '{target_str}' does not exist in the current workspace."

        if not target_path.is_dir():
            return f"ERROR: Target '{target_str}' is not a directory."

        try:
            # Generate the tree structure
            # If target is ".", use the project root directory name as label
            root_label = target_str if target_str and target_str != "." else target_path.name
            lines = [root_label]
            lines.extend(self._generate_tree_lines(target_path))
            tree_content = "\n".join(lines)
        except OSError as e:
            return f"ERROR: Failed to build directory tree for '{target_str}': {e}"
        else:
            return f"### Directory Tree: {target_str}\n```text\n{tree_content}\n```"

    def _generate_tree_lines(
        self, dir_path: Path, prefix: str = ""
    ) -> typing.Generator[str, None, None]:
        """
        Recursively yields tree lines for the contents of dir_path.

        Args:
            dir_path: The directory path to process.
            prefix: The indentation prefix for the current line.

        Yields:
            str: Each line of the ASCII tree.

        """
        try:
            # Collect and sort children: directories first, then files alphabetically
            # Filtering out excluded directories
            items = [item for item in dir_path.iterdir() if item.name not in self.EXCLUDE]

            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

            count = len(items)
            for i, item in enumerate(items):
                is_last = i == count - 1
                connector = "└── " if is_last else "├── "

                # Yield the current item's tree line
                yield f"{prefix}{connector}{item.name}"

                # If item is a directory, recurse
                if item.is_dir():
                    extension = "    " if is_last else "│   "
                    yield from self._generate_tree_lines(item, prefix + extension)

        except PermissionError:
            yield f"{prefix} [Permission Denied]"
        except OSError as e:
            yield f"{prefix} [Error: {e}]"
