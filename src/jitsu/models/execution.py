"""Execution models for the Jitsu autonomous agent."""

from pydantic import BaseModel, ConfigDict


class FileEdit(BaseModel):
    """A single file edit proposed by the agent."""

    model_config = ConfigDict(frozen=True)

    filepath: str
    content: str


class ExecutionResult(BaseModel):
    """The structured output of an autonomous execution step."""

    model_config = ConfigDict(frozen=True)

    thoughts: str
    edits: list[FileEdit]


class VerificationFailureDetails(BaseModel):
    """Details about a verification failure."""

    model_config = ConfigDict(frozen=True)

    summary: str
    trimmed: str
    failed_cmd: str
    failing_file: str | None = None
