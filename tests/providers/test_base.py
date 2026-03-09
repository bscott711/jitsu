"""Unit tests for the Jitsu Provider base interface."""

import pytest

from jitsu.providers.base import BaseProvider


class DummyProvider(BaseProvider):
    """A concrete implementation of BaseProvider for testing purposes."""

    @property
    def name(self) -> str:
        """Return the dummy provider name."""
        return "dummy_provider"

    async def resolve(self, target: str) -> str:
        """Return a simple resolved string."""
        return f"Resolved target: {target}"


def test_cannot_instantiate_base_provider() -> None:
    """Ensure BaseProvider cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseProvider()  # type: ignore


async def test_dummy_provider_implementation() -> None:
    """Test that a valid subclass correctly implements the interface."""
    provider = DummyProvider()

    # Test the property
    assert provider.name == "dummy_provider"

    # Test the async resolution
    result = await provider.resolve("test_model")
    assert result == "Resolved target: test_model"
