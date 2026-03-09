"""Strictly controlled logging utility for Jitsu."""

import logging
import sys

# Pyright Fix: Use lowercase for mutable module-level state
# Track initialized loggers by name to prevent duplicate handlers while
# ensuring every newly requested logger is properly configured.
_configured_loggers: set[str] = set()


def get_logger(name: str = "jitsu") -> logging.Logger:
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

    if name not in _configured_loggers:
        logger.setLevel(logging.INFO)
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

        _configured_loggers.add(name)

    return logger
