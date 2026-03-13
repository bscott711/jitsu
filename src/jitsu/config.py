"""Configuration management for Jitsu."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class JitsuSettings(BaseSettings):
    """
    Settings for the Jitsu application.

    Models can be configured via environment variables (e.g., JITSU_PLANNER_MODEL)
    or a .env file.
    """

    planner_model: str = "openrouter/hunter-alpha"
    executor_model: str = "openrouter/hunter-alpha"
    backup_model: str = "stepfun/step-3.5-flash:free"

    # Support reading from .env or jitsu.toml (via pydantic-settings)
    # Default search path is current working directory
    model_config = SettingsConfigDict(
        env_prefix="JITSU_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Global settings instance
settings = JitsuSettings()


def get_settings() -> JitsuSettings:
    """Return the global settings instance."""
    return settings
