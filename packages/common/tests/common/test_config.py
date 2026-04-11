"""
Test suite for the configuration loading utilities.

This module tests the `BaseServiceConfig` class, ensuring it correctly
loads settings from `.env` and `config.toml` files, respects precedence rules,
ignores extra fields, and enforces required fields using Pydantic's validation.
"""

from pathlib import Path

import pytest
from common.config import BaseServiceConfig
from pydantic import ValidationError


@pytest.fixture
def temp_config_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Create a temporary directory with mock `.env` and `config.toml` files.

    Changes the working directory via `monkeypatch.chdir` so Pydantic
    resolves the configuration files from this isolated environment.
    """
    d = tmp_path / "config"
    d.mkdir()

    env_file = d / ".env"
    env_file.write_text("DEBUG=true\nAPI_KEY=secret", encoding="utf-8")

    toml_file = d / "config.toml"
    toml_file.write_text('title = "MyService"\nport = 8080', encoding="utf-8")

    monkeypatch.chdir(d)
    return d


def test_config_loads_from_toml(temp_config_files: Path) -> None:
    """Verify that configuration values are correctly loaded from a TOML file."""

    class TestConfig(BaseServiceConfig):
        """Test model."""

        title: str
        port: int

    config = TestConfig(**{})
    assert config.title == "MyService"
    assert config.port == 8080


def test_config_loads_from_env(temp_config_files: Path) -> None:
    """Verify that configuration values are correctly loaded from a .env file."""

    class TestConfig(BaseServiceConfig):
        """Test model."""

        DEBUG: bool
        API_KEY: str

    config = TestConfig(**{})
    assert config.DEBUG is True
    assert config.API_KEY == "secret"


def test_extra_fields_are_ignored(temp_config_files: Path) -> None:
    """Ensure extra fields present in the config files are safely ignored."""

    class TestConfig(BaseServiceConfig):
        """Test model."""

        title: str

    config = TestConfig(**{})
    assert config.title == "MyService"
    assert not hasattr(config, "port")


def test_missing_required_field_raises_error(temp_config_files: Path) -> None:
    """Check that a ValidationError is raised if a required field is missing."""

    class TestConfig(BaseServiceConfig):
        """Test model."""

        missing_field: str

    with pytest.raises(ValidationError):
        TestConfig(**{})


def test_env_overrides_toml(temp_config_files: Path) -> None:
    """Confirm that environment variables take precedence over TOML file values."""
    env_file = temp_config_files / ".env"
    env_file.write_text("PORT=9999", encoding="utf-8")

    class TestConfig(BaseServiceConfig):
        """Test model."""

        port: int

    config = TestConfig(**{})
    assert config.port == 9999
