"""Tests for the strict Jitsu logger."""

import logging

import pytest
import typer

from jitsu.utils.logger import LogManager, is_quiet, secho, set_quiet


def test_logger_routes_to_stderr_only(capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure the logger writes exclusively to stderr."""
    manager = LogManager()
    logger = manager.get_logger("test_stderr_logger")

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
    manager = LogManager()
    logger1 = manager.get_logger("test_singleton")
    initial_handler_count = len(logger1.handlers)

    logger2 = manager.get_logger("test_singleton_other")

    assert len(logger1.handlers) == initial_handler_count
    assert logger1.propagate is False
    # F841 Fix: Actually use logger2 to prove the config applies to it as well
    assert logger2.propagate is False


def test_logger_quiet_mode(capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure quiet mode suppresses INFO logs but shows ERROR."""
    manager = LogManager()
    manager.set_quiet(enabled=True)
    logger = manager.get_logger("test_quiet")

    logger.info("should be hidden")
    logger.error("should be visible")

    captured = capsys.readouterr()
    assert "should be hidden" not in captured.err
    assert "should be visible" in captured.err


def test_logger_toggle_quiet_mode(capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure toggling quiet mode affects existing loggers."""
    manager = LogManager()
    logger = manager.get_logger("test_toggle")

    # Start with info
    logger.setLevel(logging.INFO)
    logger.info("info enabled")
    captured = capsys.readouterr()
    assert "info enabled" in captured.err

    # Quiet mode on
    manager.set_quiet(enabled=True)
    logger.info("info disabled")
    captured = capsys.readouterr()
    assert "info disabled" not in captured.err

    # Quiet mode off
    manager.set_quiet(enabled=False)
    logger.info("info re-enabled")
    captured = capsys.readouterr()
    assert "info re-enabled" in captured.err


def test_secho_quiet_mode(capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure secho respect quiet mode."""
    # Save original state
    original_quiet = is_quiet()

    try:
        set_quiet(enabled=True)
        secho("hidden", fg=typer.colors.GREEN, err=True)
        secho("visible", fg=typer.colors.RED, err=True)

        captured = capsys.readouterr()
        assert "hidden" not in captured.err
        assert "visible" in captured.err

        set_quiet(enabled=False)
        secho("visible now", fg=typer.colors.GREEN, err=True)
        captured = capsys.readouterr()
        assert "visible now" in captured.err
    finally:
        set_quiet(enabled=original_quiet)
