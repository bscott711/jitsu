"""Tests for the JitsuOrchestrator."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import httpx
import openai
import pytest
import typer
from instructor.core.exceptions import InstructorRetryException

from jitsu.config import settings
from jitsu.core.executor import MonotonicityError
from jitsu.core.orchestrator import JitsuOrchestrator
from jitsu.core.storage import EpicStorage
from jitsu.models.core import AgentDirective, PhaseReport, PhaseStatus
from jitsu.models.execution import VerificationFailureDetails
from jitsu.providers.git import GitError


@pytest.mark.asyncio
async def test_orchestrator_execute_phases_success(tmp_path: Path) -> None:
    """Test JitsuOrchestrator.execute_phases on success."""
    mock_compiler = MagicMock()
    mock_compiler.compile_directive = AsyncMock(return_value="mock prompt")
    mock_executor = MagicMock()
    mock_executor.execute_directive = AsyncMock(return_value=True)
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)

    with (
        patch("shutil.which", return_value="/usr/bin/just"),
        patch("anyio.run_process", new_callable=AsyncMock) as mock_rp,
    ):
        mock_rp.return_value = MagicMock(returncode=0)
        await orchestrator.execute_phases([directive], compiler=mock_compiler)
        mock_rp.assert_awaited_once()


@pytest.mark.asyncio
async def test_orchestrator_execute_phases_failure(tmp_path: Path) -> None:
    """Test JitsuOrchestrator.execute_phases when execution fails."""
    mock_compiler = MagicMock()
    mock_compiler.compile_directive = AsyncMock(return_value="mock prompt")
    mock_executor = MagicMock()
    mock_executor.execute_directive = AsyncMock(return_value=False)
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)

    with (
        patch.object(orchestrator, "_handle_quarantine", new_callable=AsyncMock),
        pytest.raises(typer.Exit) as exc,
    ):
        await orchestrator.execute_phases([directive], compiler=mock_compiler)
    assert exc.value.exit_code == 1


@pytest.mark.asyncio
async def test_orchestrator_execute_phases_just_missing(tmp_path: Path) -> None:
    """Test JitsuOrchestrator.execute_phases when 'just' is missing."""
    mock_compiler = MagicMock()
    mock_compiler.compile_directive = AsyncMock(return_value="mock prompt")
    mock_executor = MagicMock()
    mock_executor.execute_directive = AsyncMock(return_value=True)
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)

    with patch("shutil.which", return_value=None):
        with pytest.raises(typer.Exit) as exc:
            await orchestrator.execute_phases([directive], compiler=mock_compiler)
        assert exc.value.exit_code == 1


@pytest.mark.asyncio
async def test_orchestrator_finish_success(tmp_path: Path) -> None:
    """Test JitsuOrchestrator.finish archives the epic file and cleans up branches."""
    out_file = tmp_path / "epic.json"
    out_file.write_text("[]", encoding="utf-8")
    completed_dir = tmp_path / "epics" / "completed"

    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(storage=storage)
    orchestrator._original_branch = "main"  # noqa: SLF001
    orchestrator._sandbox_branch = "jitsu-run/e1"  # noqa: SLF001

    with patch("jitsu.core.orchestrator.GitProvider") as mock_git_cls:
        mock_git = mock_git_cls.return_value
        await orchestrator.finish(out_file)
        mock_git.merge_branch.assert_called_once_with("jitsu-run/e1", "main")
        mock_git.delete_branch.assert_called_once_with("jitsu-run/e1")

    assert (completed_dir / "epic.json").exists()
    assert not out_file.exists()


@pytest.mark.asyncio
async def test_orchestrator_run_autonomous_bridge(tmp_path: Path) -> None:
    """Test JitsuOrchestrator.run_autonomous bridges to execute_phases and finish."""
    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(storage=storage)
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    with (
        patch("jitsu.core.orchestrator.GitProvider") as mock_git_cls,
        patch.object(orchestrator, "execute_phases", new_callable=AsyncMock) as mock_exec,
        patch.object(orchestrator, "finish", new_callable=AsyncMock) as mock_final,
    ):
        mock_git = mock_git_cls.return_value
        mock_git.get_current_branch.return_value = "main"
        await orchestrator.run_autonomous([directive], Path("test.json"))
        mock_exec.assert_awaited_once()
        mock_final.assert_awaited_once()
        mock_git.create_and_checkout_branch.assert_called_once_with("jitsu-run/e")


@pytest.mark.asyncio
async def test_orchestrator_run_autonomous_with_model(tmp_path: Path) -> None:
    """Test run_autonomous updates executor model."""
    storage = EpicStorage(base_dir=tmp_path)
    mock_executor = MagicMock()
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    with (
        patch("jitsu.core.orchestrator.GitProvider") as mock_git_cls,
        patch.object(orchestrator, "execute_phases", new_callable=AsyncMock),
        patch.object(orchestrator, "finish", new_callable=AsyncMock),
    ):
        mock_git = mock_git_cls.return_value
        mock_git.get_current_branch.return_value = "main"
        await orchestrator.run_autonomous([directive], Path("test.json"), model="custom-model")
        assert orchestrator.executor.model == "custom-model"


@pytest.mark.asyncio
async def test_orchestrator_execute_run_success(tmp_path: Path) -> None:
    """Test execute_run completes successfully."""
    orchestrator = JitsuOrchestrator(storage=EpicStorage(base_dir=tmp_path))
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    async def mock_plan_side_effect(
        _objective: str, _files: list[str], out: Path, **_kwargs: object
    ) -> list[AgentDirective]:
        out.parent.mkdir(parents=True, exist_ok=True)
        # The mock should write to 'out' which is now 'temp_plan.json'
        await anyio.Path(out).write_text(json.dumps([directive.model_dump()]), encoding="utf-8")
        return [directive]

    with (
        patch.object(orchestrator, "execute_plan", new_callable=AsyncMock) as mock_plan,
        patch.object(orchestrator, "send_payload", new_callable=AsyncMock) as mock_send,
        patch.object(orchestrator.storage, "archive") as mock_archive,
    ):
        mock_plan.side_effect = mock_plan_side_effect
        mock_send.return_value = "ACK"
        # The archive call should be on the final path: epics/current/e.json
        expected_out = tmp_path / "epics" / "current" / "e.json"
        mock_archive.return_value = tmp_path / "epics" / "completed" / "e.json"

        await orchestrator.execute_run("test", [], model="test", verbose=False)

        mock_plan.assert_awaited_once()
        mock_send.assert_awaited_once()
        # Verify archive was called with the correct path
        assert mock_archive.call_args[0][0] == expected_out
        assert expected_out.parent.exists()


@pytest.mark.asyncio
async def test_orchestrator_execute_run_server_error(tmp_path: Path) -> None:
    """Test execute_run handles server error response."""
    orchestrator = JitsuOrchestrator(storage=EpicStorage(base_dir=tmp_path))
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    async def mock_plan_side_effect(
        _objective: str, _files: list[str], out: Path, **_kwargs: object
    ) -> list[AgentDirective]:
        out.parent.mkdir(parents=True, exist_ok=True)
        await anyio.Path(out).write_text(json.dumps([directive.model_dump()]), encoding="utf-8")
        return [directive]

    with (
        patch.object(orchestrator, "execute_plan", new_callable=AsyncMock) as mock_plan,
        patch.object(orchestrator, "send_payload", new_callable=AsyncMock) as mock_send,
    ):
        mock_plan.side_effect = mock_plan_side_effect
        mock_send.return_value = "ERR"

        with pytest.raises(typer.Exit) as exc:
            await orchestrator.execute_run("test", [], model="test", verbose=False)
        assert exc.value.exit_code == 1


@pytest.mark.asyncio
async def test_orchestrator_execute_auto_file_success(tmp_path: Path) -> None:
    """Test execute_auto from file."""
    epic_file = tmp_path / "epic.json"
    epic_file.write_text("[]", encoding="utf-8")

    orchestrator = JitsuOrchestrator(storage=EpicStorage(base_dir=tmp_path))

    with patch.object(orchestrator, "run_autonomous", new_callable=AsyncMock) as mock_auto:
        await orchestrator.execute_auto(file=epic_file, model="test")
        mock_auto.assert_awaited_once()


@pytest.mark.asyncio
async def test_orchestrator_resume_success(tmp_path: Path) -> None:
    """Test successful resumption of a stuck epic."""
    storage = EpicStorage(base_dir=tmp_path)
    mock_executor = MagicMock()
    mock_executor.run_verification.return_value = (True, None)

    # Use a real state manager to test hydration integration
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)

    epic_id = "test-resume"
    epic_path = storage.get_current_path(epic_id)
    state_path = epic_path.with_suffix(".state")

    d1 = AgentDirective(
        epic_id=epic_id,
        phase_id="p1",
        module_scope=["s"],
        instructions="i1",
        verification_commands=["c1"],
    )
    epic_path.write_text(json.dumps([d1.model_dump()]), encoding="utf-8")

    report = PhaseReport(phase_id="p1", status=PhaseStatus.STUCK)
    state_path.write_text(report.model_dump_json(), encoding="utf-8")

    with (
        patch("jitsu.core.orchestrator.GitProvider") as mock_git_cls,
        patch.object(orchestrator, "finish", new_callable=AsyncMock) as mock_finish,
    ):
        mock_git = mock_git_cls.return_value
        mock_git.get_current_branch.return_value = "main"

        await orchestrator.resume(epic_id)

        mock_executor.run_verification.assert_called_once_with(["c1"])
        assert not state_path.exists()
        mock_finish.assert_awaited_once()


@pytest.mark.asyncio
async def test_orchestrator_resume_fails_verification(tmp_path: Path) -> None:
    """Test resume fails if verification still fails."""
    storage = EpicStorage(base_dir=tmp_path)
    mock_executor = MagicMock()

    details = VerificationFailureDetails(summary="still fails", trimmed="...", failed_cmd="c1")
    mock_executor.run_verification.return_value = (False, details)
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)

    epic_id = "test-fail"
    epic_path = storage.get_current_path(epic_id)
    state_path = epic_path.with_suffix(".state")

    d1 = AgentDirective(
        epic_id=epic_id,
        phase_id="p1",
        module_scope=["s"],
        instructions="i1",
        verification_commands=["c1"],
    )
    epic_path.write_text(json.dumps([d1.model_dump()]), encoding="utf-8")
    report = PhaseReport(phase_id="p1", status=PhaseStatus.STUCK)
    state_path.write_text(report.model_dump_json(), encoding="utf-8")

    with pytest.raises(typer.Exit) as exc:
        await orchestrator.resume(epic_id)
    assert exc.value.exit_code == 1
    assert state_path.exists()


@pytest.mark.asyncio
async def test_orchestrator_resume_with_remaining(tmp_path: Path) -> None:
    """Test resume with remaining phases."""
    storage = EpicStorage(base_dir=tmp_path)
    mock_executor = MagicMock()
    mock_executor.run_verification.return_value = (True, None)
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)

    epic_id = "test-remaining"
    epic_path = storage.get_current_path(epic_id)
    state_path = epic_path.with_suffix(".state")

    d1 = AgentDirective(epic_id=epic_id, phase_id="p1", module_scope=["s"], instructions="i1")
    d2 = AgentDirective(epic_id=epic_id, phase_id="p2", module_scope=["s"], instructions="i2")
    epic_path.write_text(json.dumps([d1.model_dump(), d2.model_dump()]), encoding="utf-8")

    report = PhaseReport(phase_id="p1", status=PhaseStatus.STUCK)
    state_path.write_text(report.model_dump_json(), encoding="utf-8")

    with (
        patch("jitsu.core.orchestrator.GitProvider") as mock_git_cls,
        patch.object(orchestrator, "execute_phases", new_callable=AsyncMock) as mock_exec,
        patch.object(orchestrator, "finish", new_callable=AsyncMock) as mock_finish,
    ):
        mock_git = mock_git_cls.return_value
        mock_git.checkout_branch.side_effect = GitError("failed")
        mock_git.get_current_branch.return_value = "main"

        await orchestrator.resume(epic_id)

        mock_exec.assert_awaited_once()
        mock_finish.assert_awaited_once()


@pytest.mark.asyncio
async def test_orchestrator_resume_hydrate_error(tmp_path: Path) -> None:
    """Test resume handles hydration errors."""
    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(storage=storage)

    with pytest.raises(typer.Exit) as exc:
        await orchestrator.resume("missing")
    assert exc.value.exit_code == 1


@pytest.mark.asyncio
async def test_orchestrator_resume_with_model(tmp_path: Path) -> None:
    """Test resume with model override."""
    storage = EpicStorage(base_dir=tmp_path)
    mock_executor = MagicMock()
    mock_executor.run_verification.return_value = (True, None)
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)

    epic_id = "test-model"
    epic_path = storage.get_current_path(epic_id)
    state_path = epic_path.with_suffix(".state")
    d1 = AgentDirective(epic_id=epic_id, phase_id="p1", module_scope=["s"], instructions="i")
    epic_path.write_text(json.dumps([d1.model_dump()]), encoding="utf-8")
    report = PhaseReport(phase_id="p1", status=PhaseStatus.STUCK)
    state_path.write_text(report.model_dump_json(), encoding="utf-8")

    with (
        patch("jitsu.core.orchestrator.GitProvider"),
        patch.object(orchestrator, "finish", new_callable=AsyncMock),
    ):
        await orchestrator.resume(epic_id, model="new-model")
        assert orchestrator.executor.model == "new-model"


@pytest.mark.asyncio
async def test_orchestrator_resume_forced(tmp_path: Path) -> None:
    """Test forced resumption skips verification."""
    storage = EpicStorage(base_dir=tmp_path)
    mock_executor = MagicMock()
    # Verification would fail if called
    mock_executor.run_verification.return_value = (False, None)
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)

    epic_id = "test-forced"
    epic_path = storage.get_current_path(epic_id)
    state_path = epic_path.with_suffix(".state")
    d1 = AgentDirective(epic_id=epic_id, phase_id="p1", module_scope=["s"], instructions="i")
    epic_path.write_text(json.dumps([d1.model_dump()]), encoding="utf-8")
    report = PhaseReport(phase_id="p1", status=PhaseStatus.STUCK)
    state_path.write_text(report.model_dump_json(), encoding="utf-8")

    with (
        patch("jitsu.core.orchestrator.GitProvider"),
        patch.object(orchestrator, "finish", new_callable=AsyncMock),
    ):
        await orchestrator.resume(epic_id, force=True)
        # Verify run_verification was NOT called
        mock_executor.run_verification.assert_not_called()
        assert not state_path.exists()


@pytest.mark.asyncio
async def test_orchestrator_execute_auto_objective_success(tmp_path: Path) -> None:
    """Test execute_auto from objective."""
    orchestrator = JitsuOrchestrator(storage=EpicStorage(base_dir=tmp_path))

    with (
        patch.object(orchestrator, "execute_plan", new_callable=AsyncMock) as mock_plan,
        # Patch archive to prevent real archiving during auto run
        patch.object(orchestrator.storage, "archive", side_effect=lambda x: x),
        patch.object(orchestrator, "run_autonomous", new_callable=AsyncMock) as mock_auto,
    ):
        directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")
        mock_plan.return_value = [directive]

        # We need to simulate the file being created
        async def side_effect(
            _objective: str, _files: list[str], _out: Path, **_kwargs: object
        ) -> list[AgentDirective]:
            await anyio.Path(_out).write_text("[]", encoding="utf-8")
            return [directive]

        mock_plan.side_effect = side_effect

        await orchestrator.execute_auto(objective="test", model="test")
        mock_plan.assert_awaited_once()
        mock_auto.assert_awaited_once()
        # Verify the path passed to run_autonomous uses epic_id
        assert mock_auto.call_args[0][1] == tmp_path / "epics" / "current" / "e.json"


@pytest.mark.asyncio
async def test_orchestrator_execute_auto_validation_error(tmp_path: Path) -> None:
    """Test execute_auto handles validation error in file."""
    epic_file = tmp_path / "epic.json"
    epic_file.write_text('{"invalid": "data"}', encoding="utf-8")

    orchestrator = JitsuOrchestrator(storage=EpicStorage(base_dir=tmp_path))

    with pytest.raises(typer.Exit) as exc:
        await orchestrator.execute_auto(file=epic_file, model="test")
    assert exc.value.exit_code == 1


@pytest.mark.asyncio
async def test_orchestrator_execute_auto_no_objective_or_file(tmp_path: Path) -> None:
    """Test execute_auto fails if neither objective nor file is provided."""
    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(storage=storage)
    with pytest.raises(typer.Exit) as exc:
        await orchestrator.execute_auto(model="test")
    assert exc.value.exit_code == 1


@pytest.mark.asyncio
async def test_orchestrator_send_payload_failure(tmp_path: Path) -> None:
    """Test _send_payload handles connection refused."""
    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(storage=storage)
    with patch("anyio.connect_tcp", side_effect=ConnectionRefusedError()):
        with pytest.raises(typer.Exit) as exc:
            await orchestrator.send_payload(b"test")
        assert exc.value.exit_code == 1


@pytest.mark.asyncio
async def test_orchestrator_send_payload_eof(tmp_path: Path) -> None:
    """Test _send_payload handles EndOfStream."""
    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(storage=storage)
    mock_client = AsyncMock()
    mock_client.receive.side_effect = anyio.EndOfStream()

    with patch(
        "anyio.connect_tcp", return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_client))
    ):
        res = await orchestrator.send_payload(b"test")
        assert "ERR" in res


@pytest.mark.asyncio
async def test_orchestrator_run_plan_success(tmp_path: Path) -> None:
    """Test run_plan success and output generation."""
    mock_planner = MagicMock()
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")
    mock_planner.generate_plan = AsyncMock(return_value=[directive])

    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(planner=mock_planner, storage=storage)
    out_file = tmp_path / "out.json"

    res = await orchestrator.run_plan("test", [], out_file, model="test")
    assert res == [directive]
    mock_planner.save_plan.assert_called_once_with(out_file)


@pytest.mark.asyncio
async def test_orchestrator_run_plan_fallback(tmp_path: Path) -> None:
    """Test run_plan fallback logic on 429."""
    mock_planner = MagicMock()
    error_response = httpx.Response(429, request=httpx.Request("POST", "url"))
    mock_error = openai.APIStatusError("limit", response=error_response, body=None)
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    mock_planner.generate_plan.side_effect = [mock_error, AsyncMock(return_value=[directive])()]

    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(planner=mock_planner, storage=storage)
    out_file = tmp_path / "out.json"

    await orchestrator.run_plan("test", [], out_file, model="test")
    expected_calls = 2
    assert mock_planner.generate_plan.call_count == expected_calls


@pytest.mark.asyncio
async def test_orchestrator_run_plan_planner_failure(tmp_path: Path) -> None:
    """Test run_plan when planner returns None/Empty."""
    mock_planner = MagicMock()
    mock_planner.generate_plan = AsyncMock(return_value=None)

    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(planner=mock_planner, storage=storage)
    out_file = tmp_path / "out.json"

    with pytest.raises(typer.Exit) as exc:
        await orchestrator.run_plan("test", [], out_file, model="test")
    assert exc.value.exit_code == 1


@pytest.mark.asyncio
async def test_orchestrator_run_plan_general_exception(tmp_path: Path) -> None:
    """Test run_plan handles general exceptions via _handle_planner_error."""
    mock_planner = MagicMock()
    mock_planner.generate_plan.side_effect = RuntimeError("fail")

    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(planner=mock_planner, storage=storage)
    out_file = tmp_path / "out.json"

    with pytest.raises(typer.Exit) as exc:
        await orchestrator.run_plan("test", [], out_file, model="test")
    assert exc.value.exit_code == 1


def test_orchestrator_handle_planner_error_instructor() -> None:
    """Test handle_planner_error with InstructorRetryException."""
    e = InstructorRetryException("fail", n_attempts=1, total_usage=0)
    with pytest.raises(typer.Exit) as exc:
        JitsuOrchestrator.handle_planner_error(e)
    assert exc.value.exit_code == 1


def test_orchestrator_handle_planner_error_api_status() -> None:
    """Test handle_planner_error with APIStatusError."""
    error_response = httpx.Response(500, request=httpx.Request("POST", "url"))
    e = openai.APIStatusError("fail", response=error_response, body=None)
    with pytest.raises(typer.Exit) as exc:
        JitsuOrchestrator.handle_planner_error(e)
    assert exc.value.exit_code == 1


def test_orchestrator_handle_planner_error_runtime() -> None:
    """Test handle_planner_error with RuntimeError (API key)."""
    e = RuntimeError("OPENROUTER_API_KEY")
    with pytest.raises(typer.Exit) as exc:
        JitsuOrchestrator.handle_planner_error(e)
    assert exc.value.exit_code == 1


@pytest.mark.asyncio
async def test_orchestrator_execute_plan_async(tmp_path: Path) -> None:
    """Test execute_plan is async and behaves correctly."""
    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(storage=storage)
    out = tmp_path / "out.json"
    with patch.object(orchestrator, "run_plan", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = ["dummy"]
        res = await orchestrator.execute_plan("test", [], out, model="test")
        assert res == ["dummy"]


@pytest.mark.asyncio
async def test_orchestrator_run_plan_on_progress(tmp_path: Path) -> None:
    """Test on_progress callback in run_plan."""
    progress_msgs = []

    def on_progress(msg: str) -> None:
        progress_msgs.append(msg)

    mock_planner = MagicMock()
    mock_planner.generate_plan = AsyncMock(
        return_value=[
            AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")
        ]
    )

    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(planner=mock_planner, on_progress=on_progress, storage=storage)
    out_file = tmp_path / "out.json"

    await orchestrator.run_plan("test", [], out_file, model="test")
    _, kwargs = mock_planner.generate_plan.call_args
    on_prog_cb = kwargs["on_progress"]
    await on_prog_cb("test message")
    assert "test message" in progress_msgs


def test_orchestrator_handle_planner_error_verbose() -> None:
    """Test handle_planner_error with verbose=True."""
    e = ValueError("fail")
    e.__cause__ = RuntimeError("cause")
    with pytest.raises(typer.Exit) as exc, patch("typer.secho"):
        JitsuOrchestrator.handle_planner_error(e, verbose=True)
    assert exc.value.exit_code == 1


@pytest.mark.asyncio
async def test_orchestrator_execute_run_os_error(tmp_path: Path) -> None:
    """Test execute_run handles OSError during file read."""
    orchestrator = JitsuOrchestrator(storage=EpicStorage(base_dir=tmp_path))

    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    async def mock_plan_side_effect(
        _objective: str, _files: list[str], out: Path, **_kwargs: object
    ) -> list[AgentDirective]:
        await anyio.Path(out).write_text("[]", encoding="utf-8")
        return [directive]

    with (
        patch.object(orchestrator, "execute_plan", new_callable=AsyncMock) as mock_plan,
        # Patch read_bytes after the rename happens
        patch.object(
            EpicStorage,
            "read_bytes",
            side_effect=OSError("Read error"),
        ),
    ):
        mock_plan.side_effect = mock_plan_side_effect
        with pytest.raises(typer.Exit) as exc:
            await orchestrator.execute_run("test", [], model="test")
        assert exc.value.exit_code == 1


@pytest.mark.asyncio
async def test_orchestrator_run_plan_fallback_fail(tmp_path: Path) -> None:
    """Test run_plan fallback failure when already using fallback model."""
    mock_planner = MagicMock()
    error_response = httpx.Response(429, request=httpx.Request("POST", "url"))
    mock_error = openai.APIStatusError("limit", response=error_response, body=None)

    # If starting with gpt-oss-120b and it fails, it should raise immediately
    mock_planner.generate_plan.side_effect = mock_error
    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(planner=mock_planner, storage=storage)
    out_file = tmp_path / "out.json"

    with pytest.raises(typer.Exit) as exc:
        await orchestrator.run_plan("test", [], out_file, model=settings.backup_model)
    assert exc.value.exit_code == 1
    assert mock_planner.generate_plan.call_count == 1


@pytest.mark.asyncio
async def test_orchestrator_execute_auto_os_error_direct(tmp_path: Path) -> None:
    """Cover OSError in execute_auto loading file."""
    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(storage=storage)
    epic_file = tmp_path / "epic.json"
    epic_file.touch()

    # Bypass run_sync to trigger OSError directly in the same thread if possible
    with patch("jitsu.core.orchestrator.run_sync", side_effect=OSError("Read fail")):
        with pytest.raises(typer.Exit) as exc:
            await orchestrator.execute_auto(file=epic_file, model="test")
        assert exc.value.exit_code == 1


@pytest.mark.asyncio
async def test_orchestrator_send_payload_direct(tmp_path: Path) -> None:
    """Cover the decode line in _send_payload."""
    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(storage=storage)
    mock_client = MagicMock()
    mock_client.receive = AsyncMock(return_value=b"RESPONSE")
    mock_client.send = AsyncMock()
    mock_client.send_eof = AsyncMock()

    with patch(
        "jitsu.core.orchestrator.anyio.connect_tcp",
        return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_client)),
    ):
        res = await orchestrator.send_payload(b"CMD")
        assert res == "RESPONSE"


@pytest.mark.asyncio
async def test_orchestrator_execute_phases_stuck(tmp_path: Path) -> None:
    """Test JitsuOrchestrator.execute_phases when executor raises MonotonicityError."""
    mock_compiler = MagicMock()
    mock_compiler.compile_directive = AsyncMock(return_value="mock prompt")
    mock_executor = MagicMock()
    mock_executor.execute_directive = AsyncMock(side_effect=MonotonicityError("Stuck"))
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    out_file = tmp_path / "epic.json"
    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)

    with (
        patch.object(orchestrator, "_handle_quarantine", new_callable=AsyncMock) as mock_quarantine,
    ):
        with pytest.raises(typer.Exit) as exc:
            await orchestrator.execute_phases([directive], compiler=mock_compiler, out=out_file)
        assert exc.value.exit_code == 1
        mock_quarantine.assert_awaited_once()

    # Assert disk write (state file)
    state_file = out_file.with_suffix(".state")
    assert state_file.exists()
    content = json.loads(state_file.read_text())
    assert content["status"] == "STUCK"
    assert "Stuck" in content["agent_notes"]


@pytest.mark.asyncio
async def test_orchestrator_execute_phases_failed_persistence(tmp_path: Path) -> None:
    """Test JitsuOrchestrator.execute_phases when execution fails (not stuck)."""
    mock_compiler = MagicMock()
    mock_compiler.compile_directive = AsyncMock(return_value="mock prompt")
    mock_executor = MagicMock()
    mock_executor.execute_directive = AsyncMock(return_value=False)
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    out_file = tmp_path / "epic.json"
    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)

    with (
        patch.object(orchestrator, "_handle_quarantine", new_callable=AsyncMock) as mock_quarantine,
    ):
        with pytest.raises(typer.Exit) as exc:
            await orchestrator.execute_phases([directive], compiler=mock_compiler, out=out_file)
        assert exc.value.exit_code == 1
        mock_quarantine.assert_awaited_once()

    # Assert disk write (state file)
    state_file = out_file.with_suffix(".state")
    assert state_file.exists()
    content = json.loads(state_file.read_text())
    assert content["status"] == "STUCK"


@pytest.mark.asyncio
async def test_orchestrator_execute_phases_commit_failure(tmp_path: Path) -> None:
    """Test execute_phases when the commit command fails."""
    mock_compiler = MagicMock()
    mock_compiler.compile_directive = AsyncMock(return_value="prompt")
    mock_executor = MagicMock()
    mock_executor.execute_directive = AsyncMock(return_value=True)
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)

    with (
        patch("shutil.which", return_value="/usr/bin/just"),
        patch("anyio.run_process", new_callable=AsyncMock) as mock_rp,
        patch("typer.secho"),
    ):
        # Only one call to run_process (for commit)
        mock_rp.return_value = MagicMock(returncode=1, stderr=b"Commit error")
        with pytest.raises(typer.Exit) as exc:
            await orchestrator.execute_phases([directive], compiler=mock_compiler)
        assert exc.value.exit_code == 1


def test_handle_planner_error_instructor_verbose_direct() -> None:
    """Cover the verbose CAUSE branch for InstructorRetryException."""
    cause = ValueError("OriginalCause")
    e = InstructorRetryException("fail", n_attempts=1, total_usage=0)
    e.__cause__ = cause

    with patch("typer.secho") as mock_secho, pytest.raises(typer.Exit):
        JitsuOrchestrator.handle_planner_error(e, verbose=True)

    calls = [str(c[0][0]) for c in mock_secho.call_args_list]
    assert any("CAUSE" in c for c in calls)
    assert any("OriginalCause" in c for c in calls)


def test_handle_planner_error_general_verbose_direct() -> None:
    """Cover the verbose CAUSE branch for general Exception."""
    cause = RuntimeError("GeneralCause")
    e = Exception("GeneralError")
    e.__cause__ = cause

    with patch("typer.secho") as mock_secho, pytest.raises(typer.Exit):
        JitsuOrchestrator.handle_planner_error(e, verbose=True)

    calls = [str(c[0][0]) for c in mock_secho.call_args_list]
    assert any("DEBUG" in c for c in calls)
    assert any("CAUSE" in c for c in calls)
    assert any("GeneralCause" in c for c in calls)


@pytest.mark.asyncio
async def test_orchestrator_handle_quarantine_success(tmp_path: Path) -> None:
    """Test _handle_quarantine commits and restores branch."""
    orchestrator = JitsuOrchestrator(storage=EpicStorage(base_dir=tmp_path))
    orchestrator._original_branch = "main"  # noqa: SLF001
    orchestrator._sandbox_branch = "jitsu-run/e1"  # noqa: SLF001

    with (
        patch("jitsu.core.orchestrator.GitProvider") as mock_git_cls,
        patch("shutil.which", return_value="/usr/bin/just"),
        patch("anyio.run_process", new_callable=AsyncMock) as mock_rp,
    ):
        mock_git = mock_git_cls.return_value
        await orchestrator._handle_quarantine()  # noqa: SLF001

        mock_rp.assert_awaited_once()
        assert "commit" in mock_rp.call_args[0][0]
        assert "HALTED" in mock_rp.call_args[0][0][2]
        mock_git.checkout_branch.assert_called_once_with("main")


@pytest.mark.asyncio
async def test_orchestrator_handle_quarantine_no_branches() -> None:
    """Cover the branch-check guard in _handle_quarantine."""
    orchestrator = JitsuOrchestrator()
    # No branches set
    await orchestrator._handle_quarantine()  # noqa: SLF001


@pytest.mark.asyncio
async def test_orchestrator_handle_quarantine_git_failure() -> None:
    """Cover the exception catch in _handle_quarantine."""
    orchestrator = JitsuOrchestrator()
    orchestrator._original_branch = "main"  # noqa: SLF001
    orchestrator._sandbox_branch = "jitsu-run/e1"  # noqa: SLF001

    with (
        patch("jitsu.core.orchestrator.GitProvider") as mock_git_cls,
        patch("shutil.which", return_value="/usr/bin/just"),
        patch("anyio.run_process", new_callable=AsyncMock),
    ):
        mock_git = mock_git_cls.return_value
        mock_git.checkout_branch.side_effect = GitError("fail")
        await orchestrator._handle_quarantine()  # noqa: SLF001


@pytest.mark.asyncio
async def test_orchestrator_retry_budget_limit(tmp_path: Path) -> None:
    """Test that hitting MAX_RETRIES triggers STUCK state and quarantine."""
    mock_compiler = MagicMock()
    mock_compiler.compile_directive = AsyncMock(return_value="mock prompt")
    mock_executor = MagicMock()
    # Return False to simulate exhaustion of retries
    mock_executor.execute_directive = AsyncMock(return_value=False)
    directive = AgentDirective(epic_id="e", phase_id="p", module_scope=["s"], instructions="i")

    storage = EpicStorage(base_dir=tmp_path)
    state_manager = MagicMock()
    orchestrator = JitsuOrchestrator(
        executor=mock_executor, storage=storage, state_manager=state_manager
    )

    with (
        patch.object(orchestrator, "_handle_quarantine", new_callable=AsyncMock) as mock_quarantine,
        pytest.raises(typer.Exit),
    ):
        await orchestrator.execute_phases([directive], compiler=mock_compiler)

    # Assert that the status was updated to STUCK
    state_manager.update_phase.assert_called_once()
    report = state_manager.update_phase.call_args[0][0]
    assert report.status == PhaseStatus.STUCK
    assert f"Max retries ({orchestrator.MAX_RETRIES})" in report.agent_notes
    mock_quarantine.assert_awaited_once()

    # Verify execute_directive was called with max_retries=5
    mock_executor.execute_directive.assert_called_once_with(
        directive, "mock prompt", max_retries=orchestrator.MAX_RETRIES
    )


@pytest.mark.asyncio
async def test_orchestrator_retry_reset_between_phases(tmp_path: Path) -> None:
    """Test that retry counter is reset (effectively) by checking executor calls."""
    mock_compiler = MagicMock()
    mock_compiler.compile_directive = AsyncMock(return_value="mock prompt")
    mock_executor = MagicMock()
    mock_executor.execute_directive = AsyncMock(return_value=True)
    d1 = AgentDirective(epic_id="e", phase_id="p1", module_scope=["s"], instructions="i")
    d2 = AgentDirective(epic_id="e", phase_id="p2", module_scope=["s"], instructions="i")

    storage = EpicStorage(base_dir=tmp_path)
    orchestrator = JitsuOrchestrator(executor=mock_executor, storage=storage)

    with (
        patch("shutil.which", return_value="/usr/bin/just"),
        patch("anyio.run_process", new_callable=AsyncMock) as mock_rp,
    ):
        mock_rp.return_value = MagicMock(returncode=0)
        directives = [d1, d2]
        await orchestrator.execute_phases(directives, compiler=mock_compiler)

        # Verify it was called twice, both times with max_retries=5
        assert mock_executor.execute_directive.call_count == len(directives)
        calls = mock_executor.execute_directive.call_args_list
        # Accessing by index for safety with mock objects
        assert calls[0].kwargs["max_retries"] == orchestrator.MAX_RETRIES
        assert calls[1].kwargs["max_retries"] == orchestrator.MAX_RETRIES


@pytest.mark.asyncio
async def test_orchestrator_execute_plan_progress(tmp_path: Path) -> None:
    """Test progress reporting in execute_plan."""
    storage = EpicStorage(base_dir=tmp_path)
    mock_planner = MagicMock()

    async def _mock_gen_plan(*_args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        on_prog = kwargs.get("on_progress")
        if on_prog:
            await on_prog("triggered")

    mock_planner.generate_plan = AsyncMock(side_effect=_mock_gen_plan)

    progress_msgs = []

    async def on_progress(msg: str) -> None:
        progress_msgs.append(msg)

    orchestrator = JitsuOrchestrator(planner=mock_planner, on_progress=on_progress, storage=storage)
    out = tmp_path / "out.json"

    with (
        patch("typer.progressbar") as mock_pb_cls,
        patch.object(orchestrator, "run_plan", wraps=orchestrator.run_plan),
    ):
        mock_pb = mock_pb_cls.return_value.__enter__.return_value
        with pytest.raises(typer.Exit):
            await orchestrator.execute_plan("objective", [], out, model="test")

        # Verify that progress.label was set
        assert mock_pb.label is not None
        # Verify that our async on_progress was called
        assert len(progress_msgs) > 0


@pytest.mark.asyncio
async def test_orchestrator_execute_plan_progress_sync(tmp_path: Path) -> None:
    """Test sync progress reporting in execute_plan."""
    storage = EpicStorage(base_dir=tmp_path)
    mock_planner = MagicMock()

    async def _mock_gen_plan(*_args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        on_prog = kwargs.get("on_progress")
        if on_prog:
            await on_prog("triggered")

    mock_planner.generate_plan = AsyncMock(side_effect=_mock_gen_plan)

    progress_msgs = []

    def on_progress_sync(msg: str) -> None:
        progress_msgs.append(msg)

    orchestrator = JitsuOrchestrator(
        planner=mock_planner, on_progress=on_progress_sync, storage=storage
    )
    out = tmp_path / "out.json"

    with patch("typer.progressbar") as mock_pb_cls:
        mock_pb = mock_pb_cls.return_value.__enter__.return_value
        with pytest.raises(typer.Exit):
            await orchestrator.execute_plan("objective", [], out, model="test")

        assert len(progress_msgs) > 0
        assert mock_pb.label is not None


@pytest.mark.asyncio
async def test_orchestrator_run_plan_on_progress_async(tmp_path: Path) -> None:
    """Test run_plan with an async progress callback."""
    orchestrator = JitsuOrchestrator()
    mock_planner = MagicMock()
    mock_planner.generate_plan = AsyncMock()
    orchestrator.planner = mock_planner
    out_file = tmp_path / "plan.json"

    progress_msgs = []

    async def on_progress(msg: str) -> None:
        progress_msgs.append(msg)

    orchestrator.on_progress = on_progress
    await orchestrator.run_plan("test", [], out_file, model="test")

    _, kwargs = mock_planner.generate_plan.call_args
    on_prog_cb = kwargs["on_progress"]
    await on_prog_cb("test message")
    assert "test message" in progress_msgs
