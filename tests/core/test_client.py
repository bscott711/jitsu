"""Tests for the LLM client factory."""

import os
from unittest.mock import patch

import pytest

from jitsu.core.client import LLMClientFactory


def test_llm_client_factory_create_success() -> None:
    """Test successful creation of an instructor client."""
    with (
        patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}),
        patch("jitsu.core.client.OpenAI") as mock_openai,
        patch("jitsu.core.client.instructor.from_openai") as mock_instructor,
    ):
        client = LLMClientFactory.create()

        # Check interaction
        mock_openai.assert_called_once()
        mock_instructor.assert_called_once()
        assert client == mock_instructor.return_value


def test_llm_client_factory_create_missing_key() -> None:
    """Test creation fails when API key is missing."""
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("jitsu.core.client.dotenv.load_dotenv"),
        pytest.raises(RuntimeError, match="OPENROUTER_API_KEY environment variable is not set"),
    ):
        LLMClientFactory.create()
