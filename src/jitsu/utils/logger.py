"""Strictly controlled logging utility for Jitsu."""

import logging
import sys
from typing import Any

import typer


class LogManager:
    """Manages strictly configured loggers."""

    def __init__(self) -> None:
        """Initialize the logger manager context."""
        self._configured_loggers: set[str] = set()
        self._quiet: bool = False

    def is_quiet(self) -> bool:
        """Check if quiet mode is enabled."""
        return self._quiet

    def set_quiet(self, *, enabled: bool) -> None:
        """Set the quiet mode for all configured loggers."""
        self._quiet = enabled
        level = logging.ERROR if enabled else logging.INFO
        for name in self._configured_loggers:
            logging.getLogger(name).setLevel(level)

    def get_logger(self, name: str = "jitsu") -> logging.Logger:
        """
        Retrieve a logger strictly bound to sys.stderr.

        This prevents Jitsu logs from polluting sys.stdout, which is
        reserved exclusively for the MCP JSON-RPC protocol.

        Args:
            name: The name of the logger instance.

        Returns:
            A strictly configured logging.Logger instance.

        """
        # We must bypass our own banned-api rule here because this IS the safe wrapper.
        logger = logging.getLogger(name)

        if name not in self._configured_loggers:
            level = logging.ERROR if self._quiet else logging.INFO
            logger.setLevel(level)
            # CRITICAL: Do not propagate to the root logger. If another package
            # sets up a root logger on stdout, it would catch our logs and crash MCP.
            logger.propagate = False

            # strictly bind to stderr
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            self._configured_loggers.add(name)

        return logger


# Global instance
_manager = LogManager()


def get_logger(name: str = "jitsu") -> logging.Logger:
    """Retrieve a strictly configured logger."""
    return _manager.get_logger(name)


def set_quiet(*, enabled: bool) -> None:
    """Toggle quiet mode globally."""
    _manager.set_quiet(enabled=enabled)


def is_quiet() -> bool:
    """Check if quiet mode is enabled globally."""
    return _manager.is_quiet()


def secho(message: str, **kwargs: Any) -> None:  # noqa: ANN401
    """
    Wrap typer.secho to respect the global quiet mode.

    If quiet mode is enabled, only messages with fg=typer.colors.RED
    (errors) will be printed.
    """
    if _manager.is_quiet():
        # Only allow red (errors) or explicit error-like colors
        fg = kwargs.get("fg")
        if fg != typer.colors.RED:
            return

    typer.secho(message, **kwargs)
