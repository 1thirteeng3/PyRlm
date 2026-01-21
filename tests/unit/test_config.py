"""Tests for configuration module."""

import os

import pytest
from pydantic import SecretStr

from rlm.config.settings import RLMSettings


class TestRLMSettings:
    """Tests for RLMSettings configuration."""

    def test_default_values(self):
        """Should have sensible defaults."""
        # Create settings without env vars
        settings = RLMSettings(
            _env_file=None,  # Disable .env loading
        )
        assert settings.api_provider == "openai"
        assert settings.execution_mode == "docker"
        assert settings.cost_limit_usd == 5.0
        assert settings.max_recursion_depth == 5

    def test_api_key_from_env(self, monkeypatch):
        """Should load API key from environment."""
        monkeypatch.setenv("RLM_API_KEY", "test-key-123")
        settings = RLMSettings(_env_file=None)
        assert settings.api_key.get_secret_value() == "test-key-123"

    def test_provider_validation(self, monkeypatch):
        """Should validate provider options."""
        monkeypatch.setenv("RLM_API_PROVIDER", "openai")
        settings = RLMSettings(_env_file=None)
        assert settings.api_provider == "openai"

    def test_execution_mode_options(self, monkeypatch):
        """Should accept valid execution modes."""
        monkeypatch.setenv("RLM_EXECUTION_MODE", "docker")
        settings = RLMSettings(_env_file=None)
        assert settings.execution_mode == "docker"

        monkeypatch.setenv("RLM_EXECUTION_MODE", "local")
        settings = RLMSettings(_env_file=None)
        assert settings.execution_mode == "local"

    def test_has_api_key_property(self, monkeypatch):
        """Should correctly report if API key is set."""
        # Without key
        settings = RLMSettings(_env_file=None)
        assert settings.has_api_key is False

        # With key
        monkeypatch.setenv("RLM_API_KEY", "test-key")
        settings = RLMSettings(_env_file=None)
        assert settings.has_api_key is True

    def test_numeric_limits(self, monkeypatch):
        """Should respect numeric value limits."""
        monkeypatch.setenv("RLM_COST_LIMIT_USD", "10.0")
        monkeypatch.setenv("RLM_MAX_RECURSION_DEPTH", "10")
        settings = RLMSettings(_env_file=None)
        assert settings.cost_limit_usd == 10.0
        assert settings.max_recursion_depth == 10

    def test_security_settings(self, monkeypatch):
        """Should load security-related settings."""
        monkeypatch.setenv("RLM_ENTROPY_THRESHOLD", "5.0")
        monkeypatch.setenv("RLM_SIMILARITY_THRESHOLD", "0.9")
        settings = RLMSettings(_env_file=None)
        assert settings.entropy_threshold == 5.0
        assert settings.similarity_threshold == 0.9
