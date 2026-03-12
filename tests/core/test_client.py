"""Tests for the LLMClientFactory."""

from unittest.mock import MagicMock, patch

import pytest

from jitsu.core.client import LLMClientFactory


def test_client_factory_creates_client() -> None:
    """Test that LLMClientFactory.create() returns an instructor client."""
    mock_openai = MagicMock()
    mock_instructor_client = MagicMock()

    with (
        patch("jitsu.core.client.dotenv.load_dotenv"),
        patch("jitsu.core.client.os.environ.get", return_value="fake-key"),
        patch("jitsu.core.client.OpenAI", return_value=mock_openai) as mock_openai_cls,
        patch("jitsu.core.client.instructor.from_openai", return_value=mock_instructor_client),
    ):
        client = LLMClientFactory.create()

    assert client is mock_instructor_client
    mock_openai_cls.assert_called_once_with(
        base_url=LLMClientFactory.DEFAULT_BASE_URL,
        api_key="fake-key",
    )


def test_client_factory_missing_api_key() -> None:
    """Test that LLMClientFactory.create() raises RuntimeError if API key is missing."""
    with (
        patch("jitsu.core.client.dotenv.load_dotenv"),
        patch("jitsu.core.client.os.environ.get", return_value=None),
        pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"),
    ):
        LLMClientFactory.create()


def test_client_factory_custom_base_url() -> None:
    """Test that LLMClientFactory.create() uses a custom base URL if provided."""
    mock_openai = MagicMock()

    with (
        patch("jitsu.core.client.dotenv.load_dotenv"),
        patch("jitsu.core.client.os.environ.get", return_value="test-key"),
        patch("jitsu.core.client.OpenAI", return_value=mock_openai) as mock_openai_cls,
        patch("jitsu.core.client.instructor.from_openai", return_value=MagicMock()),
    ):
        LLMClientFactory.create(base_url="https://custom.api.example.com/v1")

    mock_openai_cls.assert_called_once_with(
        base_url="https://custom.api.example.com/v1",
        api_key="test-key",
    )
