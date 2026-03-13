"""Utility for parsing file paths from Python tracebacks and error messages."""

import re
from pathlib import Path


def extract_filepaths(text: str) -> list[str]:
    """
    Extract unique file paths from a traceback or error output.

    Looks for patterns like:
    - File "path/to/file.py", line 123
    - path/to/file.py:123:
    - path/to/file.py:123:45:

    Args:
        text: The error output/traceback to parse.

    Returns:
        A list of unique file paths found in the text.

    """
    patterns = [
        # Standard Python traceback: File "path/to/file.py", line 123
        r'File "([^"]+\.py)"',
        # Pytest / Ruff / Pyright style: path/to/file.py:123:45 or path/to/file.py:123
        r"([\w\.\-/]+\.py):(?:\d+)(?::\d+)?",
        # Inline file path patterns, making sure we don't grab trailing colon/punctuation
        r'(?:^|\s|["\'])([\w\.\-/]+\.py)(?:$|\s|[:"\',])',
    ]

    found_paths: set[str] = set()
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            found_paths.add(match)

    return sorted(found_paths)


def filter_local_paths(paths: list[str], workspace_root: Path) -> list[str]:
    """
    Filter paths to only keep those that exist within the workspace.

    Args:
        paths: List of paths to filter.
        workspace_root: The root directory of the workspace.

    Returns:
        List of paths relative to the workspace root that exist locally.

    """
    local_paths: list[str] = []
    for path_str in paths:
        path = Path(path_str)
        if not path.is_absolute():
            path = workspace_root / path

        if path.exists() and path.is_file():
            try:
                rel_path = path.relative_to(workspace_root)
                local_paths.append(str(rel_path))
            except ValueError:
                # Outside workspace
                continue

    return sorted(set(local_paths))
