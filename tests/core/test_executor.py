"""Tests for the Jitsu Executor."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jitsu.core.executor import JitsuExecutor
from jitsu.models.core import AgentDirective
from jitsu.models.execution import ExecutionResult, FileEdit


@pytest.fixture
def mock_directive() -> AgentDirective:
    """Create a mock AgentDirective."""
    return AgentDirective(
        epic_id="epic-1",
        phase_id="phase-1",
        module_scope="src",
        instructions="test instructions",
        completion_criteria=["done"],
        verification_commands=["just verify"],
    )


def test_executor_initialization() -> None:
    """Test executor initialization."""
    with (
        patch("jitsu.core.executor.dotenv.load_dotenv"),
        patch("jitsu.core.executor.os.environ.get", return_value="fake-key"),
        patch("jitsu.core.executor.OpenAI"),
        patch("jitsu.core.executor.instructor.from_openai"),
    ):
        executor = JitsuExecutor()
        assert executor.model == "google/gemini-2.0-flash-lite-001"


def test_executor_missing_api_key() -> None:
    """Test executor raises error if API key is missing."""
    with (
        patch("jitsu.core.executor.dotenv.load_dotenv"),
        patch("jitsu.core.executor.os.environ.get", return_value=None),
        pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"),
    ):
        JitsuExecutor()


def test_executor_execute_success(mock_directive: AgentDirective, tmp_path: Path) -> None:
    """Test successful directive execution."""
    mock_client = MagicMock()

    # Mock LLM response
    edit = FileEdit(filepath=str(tmp_path / "test.py"), content="print('hello')")
    result = ExecutionResult(thoughts="Fixed it", edits=[edit])
    mock_client.chat.completions.create.return_value = result

    # Mock subprocess success
    with (
        patch("jitsu.core.executor.dotenv.load_dotenv"),
        patch("jitsu.core.executor.os.environ.get", return_value="fake-key"),
        patch("jitsu.core.executor.OpenAI"),
        patch("jitsu.core.executor.instructor.from_openai", return_value=mock_client),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        executor = JitsuExecutor()
        success = executor.execute_directive(mock_directive, "compiler output")

    assert success is True
    assert (tmp_path / "test.py").read_text() == "print('hello')"
    assert mock_client.chat.completions.create.call_count == 1
    assert mock_run.call_count == 1


def test_executor_execute_retry_success(mock_directive: AgentDirective, tmp_path: Path) -> None:
    """Test successful directive execution after a retry."""
    mock_client = MagicMock()

    edit = FileEdit(filepath=str(tmp_path / "test.py"), content="print('hello')")
    result = ExecutionResult(thoughts="Fixed it", edits=[edit])
    mock_client.chat.completions.create.return_value = result

    # Mock subprocess failure then success
    with (
        patch("jitsu.core.executor.dotenv.load_dotenv"),
        patch("jitsu.core.executor.os.environ.get", return_value="fake-key"),
        patch("jitsu.core.executor.OpenAI"),
        patch("jitsu.core.executor.instructor.from_openai", return_value=mock_client),
        patch("subprocess.run") as mock_run,
    ):
        # 1st run fails, 2nd run succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="Syntax Error"),
            MagicMock(returncode=0),
        ]
        executor = JitsuExecutor()
        success = executor.execute_directive(mock_directive, "compiler output")

    assert success is True
    assert mock_client.chat.completions.create.call_count == 2  # noqa: PLR2004
    assert mock_run.call_count == 2  # noqa: PLR2004
    # Verify the second call includes the error message
    second_call_user_msg = mock_client.chat.completions.create.call_args_list[1][1]["messages"][1][
        "content"
    ]
    assert "PREVIOUS VERIFICATION FAILURE" in second_call_user_msg
    assert "Syntax Error" in second_call_user_msg


def test_executor_execute_failure(mock_directive: AgentDirective, tmp_path: Path) -> None:
    """Test directive execution failure after all retries."""
    mock_client = MagicMock()

    edit = FileEdit(filepath=str(tmp_path / "test.py"), content="print('hello')")
    result = ExecutionResult(thoughts="Fixed it", edits=[edit])
    mock_client.chat.completions.create.return_value = result

    # Mock subprocess always failure
    with (
        patch("jitsu.core.executor.dotenv.load_dotenv"),
        patch("jitsu.core.executor.os.environ.get", return_value="fake-key"),
        patch("jitsu.core.executor.OpenAI"),
        patch("jitsu.core.executor.instructor.from_openai", return_value=mock_client),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=1, stderr="Linter Error")
        executor = JitsuExecutor()
        success = executor.execute_directive(mock_directive, "compiler output")

    assert success is False
    assert (
        mock_client.chat.completions.create.call_count == 4  # noqa: PLR2004
    )  # Initial + 3 retries
    assert mock_run.call_count == 4  # noqa: PLR2004


def test_executor_llm_exception(mock_directive: AgentDirective) -> None:
    """Test that LLM exceptions are handled and count as attempts."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API down")

    with (
        patch("jitsu.core.executor.dotenv.load_dotenv"),
        patch("jitsu.core.executor.os.environ.get", return_value="fake-key"),
        patch("jitsu.core.executor.OpenAI"),
        patch("jitsu.core.executor.instructor.from_openai", return_value=mock_client),
        patch("subprocess.run"),
    ):
        executor = JitsuExecutor()
        success = executor.execute_directive(mock_directive, "compiler output")

    assert success is False
    assert mock_client.chat.completions.create.call_count == 4  # noqa: PLR2004
