"""Tests for the Jitsu Configuration."""

from pathlib import Path
from unittest.mock import patch

import pytest

from jitsu.config import JitsuSettings, get_settings


def test_config_defaults() -> None:
    """Test that the configuration has sensible defaults."""
    settings = JitsuSettings()
    assert settings.planner_model == "nvidia/nemotron-3-super-120b-a12b:free"
    assert settings.executor_model == "nvidia/nemotron-3-super-120b-a12b:free"
    assert settings.backup_model == "stepfun/step-3.5-flash:free"


def test_config_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that environment variables override defaults."""
    monkeypatch.setenv("JITSU_PLANNER_MODEL", "custom-planner")
    monkeypatch.setenv("JITSU_EXECUTOR_MODEL", "custom-executor")
    monkeypatch.setenv("JITSU_BACKUP_MODEL", "custom-backup")

    settings = JitsuSettings()
    assert settings.planner_model == "custom-planner"
    assert settings.executor_model == "custom-executor"
    assert settings.backup_model == "custom-backup"


def test_config_from_toml(tmp_path: Path) -> None:
    """
    Test that the configuration can be loaded from a file.
    Note: BaseSettings with SettingsConfigDict(env_file='.env') mostly focuses on .env.
    For toml, we would usually use a separate loader or pydantic-settings toml support.
    Requirement 2 says: "Configure the settings class to read from a root-level config file (like .env or jitsu.toml)."
    Pydantic-settings defaults to env_file=".env" in JitsuSettings.
    To support toml, we'd need Pydantic-settings[toml] and a custom loader.
    """
    env_file = tmp_path / ".env"
    env_file.write_text("JITSU_PLANNER_MODEL=env-file-planner\n", encoding="utf-8")

    # We need to tell JitsuSettings where the env file is for this test
    # since it's hardcoded to ".env" in the class.
    with patch("jitsu.config.SettingsConfigDict"):
        # Actually, it's easier to just instantiate with env_file
        settings = JitsuSettings(_env_file=env_file)
        assert settings.planner_model == "env-file-planner"


def test_get_settings() -> None:
    """Test the get_settings helper."""
    settings = get_settings()
    assert isinstance(settings, JitsuSettings)
