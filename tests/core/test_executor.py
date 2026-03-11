"""Tests for the Jitsu Executor."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import openai
import pytest
from instructor.core.exceptions import InstructorRetryException

from jitsu.core.executor import JitsuExecutor
from jitsu.models.core import AgentDirective
from jitsu.models.execution import ExecutionResult, FileEdit
from jitsu.prompts import EXECUTOR_SYSTEM_PROMPT


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


@pytest.fixture
def mock_runner() -> MagicMock:
    """Create a mock CommandRunner."""
    return MagicMock()


def test_executor_initialization() -> None:
    """Test executor initialization with injected client and runner."""
    mock_client = MagicMock()
    mock_runner = MagicMock()
    executor = JitsuExecutor(client=mock_client, runner=mock_runner)
    assert executor.model == "openai/gpt-oss-120b:free"
    assert executor.client is mock_client
    assert executor.runner is mock_runner


def test_executor_missing_api_key() -> None:
    """Test executor raises error if API key is missing (via LLMClientFactory)."""
    with (
        patch("jitsu.core.client.dotenv.load_dotenv"),
        patch("jitsu.core.client.os.environ.get", return_value=None),
        pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"),
    ):
        JitsuExecutor()


def test_executor_execute_success(
    mock_directive: AgentDirective, mock_runner: MagicMock, tmp_path: Path
) -> None:
    """Test successful directive execution."""
    mock_client = MagicMock()

    # Mock LLM response
    edit = FileEdit(filepath=str(tmp_path / "test.py"), content="print('hello')")
    result = ExecutionResult(thoughts="Fixed it", edits=[edit])
    mock_client.chat.completions.create.return_value = result

    # Mock runner success
    mock_runner.run.return_value = MagicMock(returncode=0)

    executor = JitsuExecutor(client=mock_client, runner=mock_runner)
    success = executor.execute_directive(mock_directive, "compiler output")

    assert success is True
    assert (tmp_path / "test.py").read_text() == "print('hello')"
    assert mock_client.chat.completions.create.call_count == 1
    assert mock_runner.run.call_count == 1

    # Verify the system prompt uses the EXECUTOR_SYSTEM_PROMPT constant
    call_args = mock_client.chat.completions.create.call_args[1]
    system_msg = call_args["messages"][0]["content"]
    assert (
        EXECUTOR_SYSTEM_PROMPT.format(
            module_scope=mock_directive.module_scope,
            anti_patterns=", ".join(mock_directive.anti_patterns),
        )
        in system_msg
    )


def test_executor_execute_retry_success(
    mock_directive: AgentDirective, mock_runner: MagicMock, tmp_path: Path
) -> None:
    """Test successful directive execution after a retry."""
    mock_client = MagicMock()

    edit = FileEdit(filepath=str(tmp_path / "test.py"), content="print('hello')")
    result = ExecutionResult(thoughts="Fixed it", edits=[edit])
    mock_client.chat.completions.create.return_value = result

    # 1st run fails, 2nd run succeeds
    mock_runner.run.side_effect = [
        MagicMock(returncode=1, stderr="Syntax Error"),
        MagicMock(returncode=0),
    ]

    executor = JitsuExecutor(client=mock_client, runner=mock_runner)
    success = executor.execute_directive(mock_directive, "compiler output")

    assert success is True
    assert mock_client.chat.completions.create.call_count == 2  # noqa: PLR2004
    assert mock_runner.run.call_count == 2  # noqa: PLR2004
    # Verify the second call includes the error message
    second_call_user_msg = mock_client.chat.completions.create.call_args_list[1][1]["messages"][1][
        "content"
    ]
    assert "PREVIOUS VERIFICATION FAILURE" in second_call_user_msg
    assert "Syntax Error" in second_call_user_msg


def test_executor_execute_failure(
    mock_directive: AgentDirective, mock_runner: MagicMock, tmp_path: Path
) -> None:
    """Test directive execution failure after all retries."""
    mock_client = MagicMock()

    edit = FileEdit(filepath=str(tmp_path / "test.py"), content="print('hello')")
    result = ExecutionResult(thoughts="Fixed it", edits=[edit])
    mock_client.chat.completions.create.return_value = result

    # Mock runner always fails
    mock_runner.run.return_value = MagicMock(returncode=1, stderr="Linter Error")

    executor = JitsuExecutor(client=mock_client, runner=mock_runner)
    success = executor.execute_directive(mock_directive, "compiler output")

    assert success is False
    assert (
        mock_client.chat.completions.create.call_count == 4  # noqa: PLR2004
    )  # Initial + 3 retries
    assert mock_runner.run.call_count == 4  # noqa: PLR2004


def test_executor_llm_exception(mock_directive: AgentDirective, mock_runner: MagicMock) -> None:
    """Test that LLM exceptions are handled and count as attempts."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API down")

    executor = JitsuExecutor(client=mock_client, runner=mock_runner)
    success = executor.execute_directive(mock_directive, "compiler output")

    assert success is False
    assert mock_client.chat.completions.create.call_count == 4  # noqa: PLR2004


def test_executor_openai_api_error(mock_directive: AgentDirective, mock_runner: MagicMock) -> None:
    """Test that OpenAI API errors cause immediate failure."""
    mock_client = MagicMock()
    # Create a mock error response
    mock_response = MagicMock()
    mock_response.status_code = 403
    error = openai.APIStatusError("Limit hit", response=mock_response, body=None)
    mock_client.chat.completions.create.side_effect = error

    with patch("typer.secho") as mock_secho:
        executor = JitsuExecutor(client=mock_client, runner=mock_runner)
        success = executor.execute_directive(mock_directive, "compiler output")

    assert success is False
    assert mock_client.chat.completions.create.call_count == 1
    mock_secho.assert_called_once()
    assert "Execution API Error [403]" in mock_secho.call_args[0][0]


def test_executor_instructor_retry_error(
    mock_directive: AgentDirective, mock_runner: MagicMock
) -> None:
    """Test that Instructor retry errors cause immediate failure."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = InstructorRetryException(
        "Failed", last_completion=None, n_attempts=3, total_usage=0
    )

    with patch("typer.secho") as mock_secho:
        executor = JitsuExecutor(client=mock_client, runner=mock_runner)
        success = executor.execute_directive(mock_directive, "compiler output")

    assert success is False
    assert mock_client.chat.completions.create.call_count == 1
    mock_secho.assert_called_once()
    assert "Failed to generate valid schema" in mock_secho.call_args[0][0]
