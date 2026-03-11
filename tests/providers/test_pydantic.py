"""Tests for the Pydantic V2 provider."""

from unittest.mock import patch

import pytest
from pydantic import BaseModel

from jitsu.providers.pydantic import PydanticProvider


class MockModel(BaseModel):
    """A simple mock model for testing."""

    name: str
    age: int = 42


@pytest.mark.asyncio
async def test_pydantic_provider_success() -> None:
    """Test successful resolution of a Pydantic model."""
    provider = PydanticProvider()
    assert provider.name == "pydantic"
    # Use a core model that is guaranteed to be in the path
    res = await provider.resolve("jitsu.models.core.AgentDirective")

    assert "### Pydantic Model Schema: jitsu.models.core.AgentDirective" in res
    assert '"epic_id"' in res
    assert '"type": "string"' in res
    assert "```json" in res


@pytest.mark.asyncio
async def test_pydantic_provider_invalid_target() -> None:
    """Test resolution with an invalid target string."""
    provider = PydanticProvider()
    res = await provider.resolve("InvalidTargetNoDots")
    assert "**ERROR:** Invalid Pydantic target" in res


@pytest.mark.asyncio
async def test_pydantic_provider_module_not_found() -> None:
    """Test resolution when the module does not exist."""
    provider = PydanticProvider()
    res = await provider.resolve("non_existent_package_123.MyModel")
    assert "**ERROR:** Could not import module" in res


@pytest.mark.asyncio
async def test_pydantic_provider_class_not_found() -> None:
    """Test resolution when the class does not exist in the module."""
    provider = PydanticProvider()
    res = await provider.resolve("jitsu.models.core.NonExistentClass")
    assert "**ERROR:** Class 'NonExistentClass' not found" in res


@pytest.mark.asyncio
async def test_pydantic_provider_not_a_basemodel() -> None:
    """Test resolution when the target is not a Pydantic BaseModel."""
    provider = PydanticProvider()
    # BaseProvider is an abc.ABC, not a pydantic.BaseModel
    res = await provider.resolve("jitsu.providers.base.BaseProvider")
    assert "is not a Pydantic V2 'BaseModel'" in res


@pytest.mark.asyncio
async def test_pydantic_provider_unexpected_error() -> None:
    """Test resolution when an unexpected error occurs."""
    provider = PydanticProvider()
    with patch("importlib.import_module", side_effect=RuntimeError("Unexpected!")):
        res = await provider.resolve("jitsu.models.core.AgentDirective")
        assert "**ERROR:** An unexpected error occurred" in res
