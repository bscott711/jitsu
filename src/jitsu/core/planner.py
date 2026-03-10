"""Generates a sequence of AgentDirectives using an LLM."""

import json
import logging
from pathlib import Path
from typing import Any

import litellm
from pydantic import TypeAdapter, ValidationError

from jitsu.models.core import AgentDirective

logger = logging.getLogger(__name__)


class JitsuPlanner:
    """Generates a sequence of AgentDirectives using an LLM."""

    def __init__(self, objective: str, relevant_files: list[str], client: Any = None) -> None:  # noqa: ANN401
        """
        Initialize the planner.

        We suppress ANN401 (Any) here because `client` could be an instance of
        openai.AsyncOpenAI, litellm.Router, or any duck-typed async LLM client.
        """
        self.objective = objective
        self.relevant_files = relevant_files
        self.client = client
        self._directives: list[AgentDirective] = []

    def _build_prompt(self) -> str:
        """Build the prompt string to feed to the LLM."""
        files_str = "\n".join(f"- {f}" for f in self.relevant_files)
        return (
            f"Objective: {self.objective}\n\n"
            f"Relevant Files:\n{files_str}\n\n"
            "Output ONLY a JSON array of AgentDirectives."
        )

    async def generate_plan(self) -> list[AgentDirective]:
        """Query the LLM and generate a validated list of directives."""
        prompt = self._build_prompt()

        try:
            if self.client is None:
                response = await litellm.acompletion(  # type: ignore[reportUnknownMemberType]
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                )
            else:
                response = await self.client.chat.completions.create(  # type: ignore[reportUnknownMemberType]
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                )

            # Extract the mystery variable and forcefully type it as a string
            raw_content = response.choices[0].message.content  # type: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            content: str = str(raw_content) if raw_content else "[]"  # type: ignore[reportUnknownArgumentType]

            # Strip markdown code blocks if the LLM surrounds the JSON
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]

            data = json.loads(content.strip())

        except (json.JSONDecodeError, KeyError, IndexError):
            logger.exception("Failed to query LLM or parse the initial JSON response")
            return []

        try:
            adapter = TypeAdapter(list[AgentDirective])
            validated_directives = adapter.validate_python(data)
        except ValidationError:
            logger.exception("Failed to validate LLM output against AgentDirective schema")
            return []
        else:
            self._directives = validated_directives
            return self._directives

    def save_plan(self, path: str | Path) -> None:
        """Save the generated plan to disk as a JSON file."""
        file_path = Path(path).resolve()

        # Ensure parent directories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Pydantic v2 model_dump for the list
        json_data = [d.model_dump() for d in self._directives]
        file_path.write_text(json.dumps(json_data, indent=2))
