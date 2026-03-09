"""Command Line Interface main entry point for Jitsu."""

import sys
from collections.abc import Awaitable, Callable
from typing import Any

import anyio

from jitsu.server.mcp_server import run_server


def main() -> None:
    """Start the Jitsu MCP Server."""
    func: Callable[[], Awaitable[Any]] = run_server
    try:
        anyio.run(func)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":  # pragma: no cover
    main()
