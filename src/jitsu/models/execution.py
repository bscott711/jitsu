"""Execution models for the Jitsu autonomous agent."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class FileEdit(BaseModel):
    """A single file edit proposed by the agent."""

    model_config = ConfigDict(frozen=True)

    filepath: str
    content: str


class ToolRequest(BaseModel):
    """A request to execute a specific tool."""

    model_config = ConfigDict(frozen=True)

    tool_name: str
    arguments: dict[str, Any]


class ExecutionResult(BaseModel):
    """The structured output of an autonomous execution step."""

    model_config = ConfigDict(frozen=True)

    thoughts: str
    action: list[FileEdit] | ToolRequest


class VerificationFailureDetails(BaseModel):
    """Details about a verification failure."""

    model_config = ConfigDict(frozen=True)

    summary: str
    trimmed: str
    failed_cmd: str
    failing_file: str | None = None
