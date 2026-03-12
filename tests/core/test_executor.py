"""Tests for the Jitsu Executor."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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


async def test_executor_execute_success(
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
    success = await executor.execute_directive(mock_directive, "compiler output")

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


async def test_executor_execute_retry_success(
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
    success = await executor.execute_directive(mock_directive, "compiler output")

    assert success is True
    assert mock_client.chat.completions.create.call_count == 2  # noqa: PLR2004
    assert mock_runner.run.call_count == 2  # noqa: PLR2004
    # Verify the second call includes the error message
    second_call_user_msg = mock_client.chat.completions.create.call_args_list[1][1]["messages"][1][
        "content"
    ]
    assert "Directive: test instructions" in second_call_user_msg
    assert "You are in recovery mode" in second_call_user_msg
    assert "### Verification Failure" in second_call_user_msg
    assert "Command 'just verify' failed with exit code 1" in second_call_user_msg
    assert "Syntax Error" in second_call_user_msg


async def test_executor_execute_failure(
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
    success = await executor.execute_directive(mock_directive, "compiler output")

    assert success is False
    assert (
        mock_client.chat.completions.create.call_count == 4  # noqa: PLR2004
    )  # Initial + 3 retries
    assert mock_runner.run.call_count == 4  # noqa: PLR2004


async def test_executor_llm_exception(
    mock_directive: AgentDirective, mock_runner: MagicMock
) -> None:
    """Test that LLM exceptions are handled and count as attempts."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API down")

    executor = JitsuExecutor(client=mock_client, runner=mock_runner)
    success = await executor.execute_directive(mock_directive, "compiler output")

    assert success is False
    assert mock_client.chat.completions.create.call_count == 4  # noqa: PLR2004


async def test_executor_openai_api_error(
    mock_directive: AgentDirective, mock_runner: MagicMock
) -> None:
    """Test that OpenAI API errors cause immediate failure."""
    mock_client = MagicMock()
    # Create a mock error response
    mock_response = MagicMock()
    mock_response.status_code = 403
    error = openai.APIStatusError("Limit hit", response=mock_response, body=None)
    mock_client.chat.completions.create.side_effect = error

    with patch("typer.secho") as mock_secho:
        executor = JitsuExecutor(client=mock_client, runner=mock_runner)
        success = await executor.execute_directive(mock_directive, "compiler output")

    assert success is False
    assert mock_client.chat.completions.create.call_count == 1
    mock_secho.assert_called_once()
    assert "Execution API Error [403]" in mock_secho.call_args[0][0]


async def test_executor_instructor_retry_error(
    mock_directive: AgentDirective, mock_runner: MagicMock
) -> None:
    """Test that Instructor retry errors cause immediate failure."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = InstructorRetryException(
        "Failed", last_completion=None, n_attempts=3, total_usage=0
    )

    with patch("typer.secho") as mock_secho:
        executor = JitsuExecutor(client=mock_client, runner=mock_runner)
        success = await executor.execute_directive(mock_directive, "compiler output")

    assert success is False
    assert mock_client.chat.completions.create.call_count == 1
    mock_secho.assert_called_once()
    assert "Failed to generate valid schema" in mock_secho.call_args[0][0]


def test_executor_truncation_logic() -> None:
    """Test that massive traces are truncated to 20 lines."""
    massive_error = "\n".join([f"Line {i}" for i in range(100)])
    truncated = JitsuExecutor._extract_first_failure_block(massive_error)  # noqa: SLF001
    lines = truncated.splitlines()
    assert len(lines) == 20  # noqa: PLR2004
    assert lines[0] == "Line 0"
    assert lines[19] == "Line 19"


def test_executor_run_verification_structure(mock_runner: MagicMock) -> None:
    """Test the return structure of _run_verification."""
    executor = JitsuExecutor(runner=mock_runner)
    mock_runner.run.return_value = MagicMock(returncode=1, stderr="Linter Error")

    success, summary, trimmed, failed_cmd = executor._run_verification(["npm test"])  # noqa: SLF001

    assert success is False
    assert summary == "Command 'npm test' failed with exit code 1"
    assert trimmed == "Linter Error"
    assert failed_cmd == "npm test"


@pytest.mark.asyncio
async def test_executor_recovery_includes_ast(
    mock_directive: AgentDirective, mock_runner: MagicMock, tmp_path: Path
) -> None:
    """Test that recovery prompt includes AST for edited files."""
    mock_client = MagicMock()

    # Mock LLM response with a .py file edit
    edit = FileEdit(filepath=str(tmp_path / "failing_logic.py"), content="def fail(): pass")
    result = ExecutionResult(thoughts="Fixed it", edits=[edit])
    mock_client.chat.completions.create.return_value = result

    # Fail first, succeed second
    mock_runner.run.side_effect = [
        MagicMock(returncode=1, stderr="Logic Error"),
        MagicMock(returncode=0),
    ]

    executor = JitsuExecutor(client=mock_client, runner=mock_runner, workspace_root=tmp_path)

    # Mock the AST provider to avoid real file parsing
    executor.ast_provider.resolve = AsyncMock(
        return_value="### AST Structural Outline: failing_logic.py\n```python\ndef fail(): ...\n```"
    )

    await executor.execute_directive(mock_directive, "compiler output")

    assert mock_client.chat.completions.create.call_count == 2  # noqa: PLR2004
    second_call_user_msg = mock_client.chat.completions.create.call_args_list[1][1]["messages"][1][
        "content"
    ]
    assert "AST Structural Outline: failing_logic.py" in second_call_user_msg
    assert "def fail(): ..." in second_call_user_msg
