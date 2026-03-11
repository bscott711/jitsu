"""Provider for reading environment variables."""

import os

from jitsu.providers.base import BaseProvider


class EnvVarProvider(BaseProvider):
    """Resolves an environment variable name into its current value."""

    @property
    def name(self) -> str:
        """Returns the registered name of this provider."""
        return "env_var"

    async def resolve(self, target: str) -> str:
        """
        Read the environment variable.

        Args:
            target: The name of the environment variable (e.g., 'HOME').

        Returns:
            str: The value of the environment variable, or 'Not Set' if missing.

        """
        value = os.environ.get(target)
        if value is None:
            return "Not Set"
        return value
