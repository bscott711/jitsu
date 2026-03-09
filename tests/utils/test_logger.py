"""Tests for the strict Jitsu logger."""

import logging

import pytest

from jitsu.utils.logger import get_logger


def test_logger_routes_to_stderr_only(capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure the logger writes exclusively to stderr."""
    logger = get_logger("test_stderr_logger")

    logger.setLevel(logging.INFO)
    test_message = "Protocol safety check"
    logger.info(test_message)

    captured = capsys.readouterr()

    assert captured.out == "", "FATAL: Logger leaked to stdout!"
    assert test_message in captured.err
    assert "INFO" in captured.err
    assert "test_stderr_logger" in captured.err


def test_logger_singleton_handler() -> None:
    """Ensure we don't attach duplicate handlers on multiple calls."""
    logger1 = get_logger("test_singleton")
    initial_handler_count = len(logger1.handlers)

    logger2 = get_logger("test_singleton_other")

    assert len(logger1.handlers) == initial_handler_count
    assert logger1.propagate is False
    # F841 Fix: Actually use logger2 to prove the config applies to it as well
    assert logger2.propagate is False
