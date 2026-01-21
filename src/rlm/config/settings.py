"""
Centralized configuration for RLM using Pydantic Settings.

Configuration is loaded from environment variables with the RLM_ prefix,
or from a .env file in the project root.
"""

from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RLMSettings(BaseSettings):
    """
    RLM Configuration Settings.

    All settings can be overridden via environment variables with the RLM_ prefix.
    Example: RLM_API_KEY, RLM_EXECUTION_MODE, etc.
    """

    model_config = SettingsConfigDict(
        env_prefix="RLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- API Configuration ---
    api_provider: Literal["openai", "anthropic", "google"] = Field(
        default="openai",
        description="LLM provider to use for inference",
    )
    api_key: SecretStr = Field(
        default=SecretStr(""),
        description="API key for the selected provider",
    )
    model_name: str = Field(
        default="gpt-4o",
        description="Model name to use for inference",
    )

    # --- Execution Configuration ---
    execution_mode: Literal["docker", "local"] = Field(
        default="docker",
        description="Execution environment: 'docker' (secure) or 'local' (development only)",
    )
    docker_runtime: str = Field(
        default="auto",
        description="Docker runtime: 'auto' (detect runsc), 'runsc', or 'runc'",
    )
    docker_image: str = Field(
        default="python:3.11-slim",
        description="Docker image for sandbox execution",
    )
    execution_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Maximum execution time in seconds",
    )

    # --- Security Configuration ---
    memory_limit: str = Field(
        default="512m",
        description="Container memory limit",
    )
    cpu_limit: float = Field(
        default=1.0,
        ge=0.1,
        le=4.0,
        description="CPU limit in cores",
    )
    pids_limit: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Maximum number of processes in container",
    )
    network_enabled: bool = Field(
        default=False,
        description="Enable network access in sandbox (DANGEROUS - only for testing)",
    )

    # --- Safety Configuration ---
    cost_limit_usd: float = Field(
        default=5.0,
        ge=0.0,
        description="Maximum cost limit in USD per session",
    )
    max_recursion_depth: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of code execution iterations",
    )
    max_stdout_bytes: int = Field(
        default=4000,
        ge=500,
        le=50000,
        description="Maximum stdout bytes to capture",
    )

    # --- Egress Filtering ---
    entropy_threshold: float = Field(
        default=4.5,
        ge=3.0,
        le=6.0,
        description="Shannon entropy threshold for secret detection",
    )
    min_entropy_length: int = Field(
        default=256,
        ge=32,
        le=1024,
        description="Minimum string length for entropy checking",
    )
    similarity_threshold: float = Field(
        default=0.8,
        ge=0.5,
        le=1.0,
        description="Similarity threshold for context echo detection",
    )

    # --- Paths ---
    pricing_path: Optional[Path] = Field(
        default=None,
        description="Path to custom pricing.json file",
    )

    @field_validator("api_key", mode="before")
    @classmethod
    def validate_api_key(cls, v: str | SecretStr) -> SecretStr:
        """Allow empty string for development, but warn."""
        if isinstance(v, SecretStr):
            return v
        return SecretStr(v) if v else SecretStr("")

    @property
    def has_api_key(self) -> bool:
        """Check if a valid API key is configured."""
        return bool(self.api_key.get_secret_value())


# Global settings singleton
settings = RLMSettings()
