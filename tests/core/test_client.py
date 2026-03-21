"""Tests for the LLM client factory."""

import os
from unittest.mock import MagicMock, patch

import pytest

from jitsu.core.client import LLMClientFactory


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    """Clear LLMClientFactory cache before each test."""
    LLMClientFactory.clear_cache()


def test_llm_client_factory_create_success() -> None:
    """Test successful creation of an AsyncOpenAI client."""
    with (
        patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}),
        patch("jitsu.core.client.AsyncOpenAI") as mock_openai,
    ):
        client = LLMClientFactory.create()

        # Check interaction
        mock_openai.assert_called_once()
        assert client == mock_openai.return_value


def test_llm_client_factory_create_missing_key() -> None:
    """Test creation fails when API key is missing."""
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("jitsu.core.client.dotenv.load_dotenv"),
        pytest.raises(RuntimeError, match="OPENROUTER_API_KEY environment variable is not set"),
    ):
        LLMClientFactory.create()


def test_llm_client_factory_singleton() -> None:
    """Test that create() returns cached instance for same base_url."""
    with (
        patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}),
        patch("jitsu.core.client.AsyncOpenAI") as mock_openai,
    ):
        mock_openai.side_effect = [MagicMock(name="client1"), MagicMock(name="client3")]

        client1 = LLMClientFactory.create()
        client2 = LLMClientFactory.create()

        # Should return same instance
        assert client1 is client2
        # Should only create OpenAI once
        assert mock_openai.call_count == 1

        # Different base_url should create new instance
        client3 = LLMClientFactory.create(base_url="https://other.api/v1")
        assert client3 is not client1
        expected_call_count = 2
        assert mock_openai.call_count == expected_call_count


def test_llm_client_factory_clear_cache() -> None:
    """Test that clear_cache() resets singleton behavior."""
    with (
        patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}),
        patch("jitsu.core.client.AsyncOpenAI") as mock_openai,
    ):
        mock_openai.return_value = "mock-client"

        LLMClientFactory.create()
        assert mock_openai.call_count == 1

        LLMClientFactory.clear_cache()
        LLMClientFactory.create()
        expected_call_count = 2
        assert mock_openai.call_count == expected_call_count  # Re-created after clear


def test_llm_client_factory_env_loaded_once() -> None:
    """Test that dotenv.load_dotenv() is only called once per process."""
    with (
        patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}),
        patch("jitsu.core.client.AsyncOpenAI"),
        patch("jitsu.core.client.dotenv.load_dotenv") as mock_load,
    ):
        # First call loads env
        LLMClientFactory.create()
        assert mock_load.call_count == 1

        # Second call uses cache, doesn't reload env
        LLMClientFactory.create()
        assert mock_load.call_count == 1

        # After clear, env loads again
        LLMClientFactory.clear_cache()
        LLMClientFactory.create()
        expected_call_count = 2
        assert mock_load.call_count == expected_call_count


def test_create_double_check_locking_coverage() -> None:
    """Trigger the double-check return on line 53 for coverage."""
    LLMClientFactory.clear_cache()
    # Bypass the first lock (env loading) to make the second lock the first one encountered
    LLMClientFactory._env_loaded = True

    original_lock = LLMClientFactory._lock

    class RacyLock:
        def __enter__(self) -> object:
            # Populate cache while "acquiring" the lock at line 50
            LLMClientFactory._instance_cache[LLMClientFactory.DEFAULT_BASE_URL] = "race-winner"  # type: ignore
            return original_lock.__enter__()

        def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
            original_lock.__exit__(exc_type, exc_val, exc_tb)

    with patch.object(LLMClientFactory, "_lock", new=RacyLock()):
        client = LLMClientFactory.create()
        assert client == "race-winner"
