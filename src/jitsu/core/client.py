"""Factory for creating an instructor-wrapped LLM client."""

import os

import dotenv
import instructor
from instructor.core.client import Instructor
from openai import OpenAI


class LLMClientFactory:
    """Centralizes LLM client instantiation for Jitsu core components."""

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    @classmethod
    def create(cls, base_url: str = DEFAULT_BASE_URL) -> Instructor:
        """
        Load environment, verify API key, and return an instructor client.

        Args:
            base_url: The base URL for the OpenAI-compatible API.

        Returns:
            An initialized instructor client.

        Raises:
            RuntimeError: If the OPENROUTER_API_KEY environment variable is not set.

        """
        dotenv.load_dotenv()

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            msg = "OPENROUTER_API_KEY environment variable is not set"
            raise RuntimeError(msg)

        return instructor.from_openai(
            OpenAI(
                base_url=base_url,
                api_key=api_key,
            ),
            mode=instructor.Mode.JSON,
        )
