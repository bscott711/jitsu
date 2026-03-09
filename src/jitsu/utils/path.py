"""Project root resolution utility."""

import functools
from pathlib import Path


def get_project_root() -> Path:
    """
    Find project root by searching upward for pyproject.toml.

    This is robust regardless of where the script is invoked from.
    """
    current = Path(__file__).resolve()

    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent

    msg = f"Could not find pyproject.toml. Searched upward from: {current}"
    raise RuntimeError(msg)


@functools.cache
def root() -> Path:
    """Get cached project root."""
    return get_project_root()
