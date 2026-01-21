"""
LLM Client Factory.

Provides a unified way to create LLM clients based on provider configuration.
"""

from typing import Literal, Optional

from rlm.config.settings import settings
from rlm.core.exceptions import ConfigurationError
from rlm.llm.base import BaseLLMClient


def create_llm_client(
    provider: Optional[Literal["openai", "anthropic", "google"]] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> BaseLLMClient:
    """
    Create an LLM client based on provider.

    Uses settings as defaults, but allows overrides.

    Args:
        provider: LLM provider (default: from settings)
        api_key: API key (default: from settings)
        model: Model name (default: from settings)
        **kwargs: Additional arguments passed to the client

    Returns:
        Configured LLM client

    Raises:
        ConfigurationError: If provider is unknown or API key is missing
    """
    provider = provider or settings.api_provider
    api_key = api_key or settings.api_key.get_secret_value()
    model = model or settings.model_name

    if not api_key:
        raise ConfigurationError(
            message=f"API key not configured for provider: {provider}",
            setting_name="api_key",
        )

    if provider == "openai":
        from rlm.llm.openai_client import OpenAIClient
        return OpenAIClient(api_key=api_key, model=model, **kwargs)

    elif provider == "anthropic":
        from rlm.llm.anthropic_client import AnthropicClient
        return AnthropicClient(api_key=api_key, model=model, **kwargs)

    elif provider == "google":
        from rlm.llm.google_client import GoogleClient
        return GoogleClient(api_key=api_key, model=model, **kwargs)

    else:
        raise ConfigurationError(
            message=f"Unknown LLM provider: {provider}",
            setting_name="api_provider",
            details={"valid_providers": ["openai", "anthropic", "google"]},
        )
