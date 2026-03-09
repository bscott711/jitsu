"""Tests for the Jitsu CLI main module."""

from unittest.mock import MagicMock, patch

from jitsu.cli.main import main


@patch("jitsu.cli.main.anyio.run")
def test_cli_main(mock_run: MagicMock) -> None:
    """Test the CLI entry point runs the server."""
    main()
    mock_run.assert_called_once()


@patch("jitsu.cli.main.anyio.run", side_effect=KeyboardInterrupt)
@patch("jitsu.cli.main.sys.exit")
def test_cli_keyboard_interrupt(mock_exit: MagicMock, mock_run_unused: MagicMock) -> None:
    """Test the CLI handles KeyboardInterrupt exits cleanly."""
    # Use the mock to satisfy ARG001 and PT019
    _ = mock_run_unused
    main()
    mock_exit.assert_called_once_with(0)
