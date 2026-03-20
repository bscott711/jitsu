"""Factory for creating a raw AsyncOpenAI LLM client."""

import os
import threading
from typing import ClassVar

import dotenv
from openai import AsyncOpenAI


class LLMClientFactory:
    """Centralizes LLM client instantiation for Jitsu core components."""

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    # Class-level cache for singleton behavior
    _instance_cache: ClassVar[dict[str, AsyncOpenAI]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()
    _env_loaded: ClassVar[bool] = False

    @classmethod
    def create(cls, base_url: str = DEFAULT_BASE_URL) -> AsyncOpenAI:
        """
        Load environment once, then return cached AsyncOpenAI client.

        Args:
            base_url: The base URL for the OpenAI-compatible API.

        Returns:
            A cached AsyncOpenAI client.

        Raises:
            RuntimeError: If the OPENROUTER_API_KEY environment variable is not set.

        """
        # Load env only once per process
        if not cls._env_loaded:
            with cls._lock:
                if not cls._env_loaded:  # Double-check after acquiring lock
                    dotenv.load_dotenv()
                    cls._env_loaded = True

        # Check cache first
        if base_url in cls._instance_cache:
            return cls._instance_cache[base_url]

        # Thread-safe creation
        with cls._lock:
            # Double-check after acquiring lock
            if base_url in cls._instance_cache:
                return cls._instance_cache[base_url]

            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                msg = "OPENROUTER_API_KEY environment variable is not set"
                raise RuntimeError(msg)

            # FIX: Return raw AsyncOpenAI client, not Instructor-wrapped
            client = AsyncOpenAI(
                base_url=base_url.strip(),  # Also fix trailing whitespace in URL
                api_key=api_key,
            )
            cls._instance_cache[base_url] = client
            return client

    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear the client cache.

        Useful for testing or when API credentials change.

        """
        with cls._lock:
            cls._instance_cache.clear()
            cls._env_loaded = False
