"""Generates a sequence of AgentDirectives using an LLM."""

import json
import logging
import os
from pathlib import Path

import anyio
import dotenv
import instructor
from openai import OpenAI

from jitsu.models.core import AgentDirective
from jitsu.providers.tree import DirectoryTreeProvider

logger = logging.getLogger(__name__)


class JitsuPlanner:
    """Generates a sequence of AgentDirectives using an LLM."""

    def __init__(self, objective: str, relevant_files: list[str]) -> None:
        """Initialize the planner with an objective and relevant files."""
        self.objective = objective
        self.relevant_files = relevant_files
        self._directives: list[AgentDirective] = []

    async def generate_plan(
        self, model: str = "google/gemini-2.0-flash-001"
    ) -> list[AgentDirective]:
        """Query the LLM and generate a validated list of directives."""
        dotenv.load_dotenv()

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            msg = "OPENROUTER_API_KEY environment variable is not set"
            raise RuntimeError(msg)

        # Initialize instructor with OpenAI client pointing to OpenRouter
        client = instructor.from_openai(
            OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
        )

        # Read the system prompt

        prompt_path = anyio.Path("docs/jitsu_orchestrator_prompt.md")
        if await prompt_path.exists():
            system_prompt = await prompt_path.read_text()
        else:
            system_prompt = "You are a helpful assistant."

        # Get repository skeleton
        tree_provider = DirectoryTreeProvider()
        skeleton = await tree_provider.resolve(str(Path.cwd()))

        # Build the user message
        files_str = "\n".join(f"- {f}" for f in self.relevant_files)
        user_message = (
            f"Repository Skeleton:\n{skeleton}\n\n"
            f"Objective: {self.objective}\n\n"
            f"Relevant Files:\n{files_str}"
        )

        try:
            self._directives = client.chat.completions.create(
                model=model,
                response_model=list[AgentDirective],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
        except Exception:
            logger.exception("Failed to generate plan via instructor")
            return []
        else:
            return self._directives

    def save_plan(self, path: str | Path) -> None:
        """Save the generated plan to disk as a JSON file."""
        file_path = Path(path).resolve()

        # Ensure parent directories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Pydantic v2 model_dump for the list
        json_data = [d.model_dump() for d in self._directives]
        file_path.write_text(json.dumps(json_data, indent=2))
