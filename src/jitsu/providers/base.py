"""The abstract base interface for all Jitsu Context Providers."""

import abc
from pathlib import Path


class BaseProvider(abc.ABC):
    """
    Abstract base class for all Jitsu Context Providers.

    A Context Provider is responsible for taking a specific target string
    (e.g., a file path, a class name, a database table) and resolving it into
    a deterministic, LLM-optimized string representation of that target's state.
    """

    def __init__(self, workspace_root: Path) -> None:
        """
        Initialize the provider with a workspace root.

        Args:
            workspace_root: The root directory of the workspace.

        """
        self.workspace_root = workspace_root

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        The unique string identifier for this provider.

        This must match the `provider_name` specified in a ContextTarget.

        Returns:
            str: The registered name of the provider (e.g., 'pydantic_v2').

        """

    @abc.abstractmethod
    async def resolve(self, target: str) -> str:
        """
        Resolve the target identifier into a context string.

        Args:
            target: The specific identifier to resolve (e.g., 'src.models.User').

        Returns:
            str: The resolved, LLM-optimized context string.

        """
